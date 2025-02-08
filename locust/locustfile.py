import time
import json
import random
import string
import re
from typing import Optional, Dict, Any, Callable
from urllib.parse import urljoin
from locust_plugins.distributor import Distributor
from locust.runners import WorkerRunner

import gevent
from gevent.lock import BoundedSemaphore
from locust import HttpUser, task, events, between
from locust.exception import LocustError, StopUser
import sseclient
import requests
from bs4 import BeautifulSoup
import logging

distributors = {}


class PuzzlehuntUser(HttpUser):
    """
    Base locust user class that supports Server-Sent Events (SSE) connections
    and common puzzlehunt functionality like static content loading.
    """
    abstract = True
    host = "http://localhost:8000"
    
    # Rate limit tracking
    _rate_limit_stats = {
        'puzzle_submissions': {
            'total_attempts': 0,
            'rate_limited_count': 0,
            'last_rate_limit': None,
            'time_remaining': None
        }
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self._sse_client = None
        self._connected = False
        self._event_handlers = []
        self._processing_greenlet = None
        self._should_stop = False
        self.static_cache = set()
        self.email = None
        self.password = None
        self.csrf_token = None
        self.team_id = None
        self.is_staff = False

        events.request.add_listener(self._track_rate_limits)

    def _track_rate_limits(self, request_type=None, name=None, response=None, exception=None, **kwargs):
        """Track rate limit information from puzzle submissions"""
        # Skip if no response or if it's not a puzzle submission
        if not response or not isinstance(response, requests.Response):
            return
            
        # Only track POST requests to puzzle submission endpoints
        if not (response.request.method == 'POST' and '/puzzle/' in response.url and '/submit/' in response.url):
            return
            
        # Parse the response content for rate limit messages
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            error_p = soup.find('p', class_='help is-danger')
            
            # Only increment total attempts for actual submission requests
            stats = self._rate_limit_stats['puzzle_submissions']
            stats['total_attempts'] += 1
            
            if error_p and "You have been rate limited" in error_p.text:
                stats['rate_limited_count'] += 1
                stats['last_rate_limit'] = time.time()
                
                # Try to extract the time remaining
                try:
                    time_str = error_p.text.split("You can submit answers again in ")[1].split(" seconds")[0]
                    stats['time_remaining'] = float(time_str)
                except (IndexError, ValueError):
                    stats['time_remaining'] = None
                
        except Exception:
            # If we can't parse the response, just continue
            pass
    
    @property
    def rate_limit_stats(self):
        """Get current rate limit statistics"""
        stats = self._rate_limit_stats.copy()
        puzzle_stats = stats['puzzle_submissions']
        
        # Calculate percentage of rate limited requests
        if puzzle_stats['total_attempts'] > 0:
            puzzle_stats['rate_limit_percentage'] = (
                (puzzle_stats['rate_limited_count'] / puzzle_stats['total_attempts']) * 100
            )
        else:
            puzzle_stats['rate_limit_percentage'] = 0
            
        return stats

    def on_start(self):
        """Called when a user starts running"""
        if self.is_staff:
            self._user_id = next(distributors["staff"])
        else:
            self._user_id = next(distributors["users"])

        if not self.email:
            if self.is_staff:
                self.email = f"staff{self._user_id}@example.com"
            else:
                self.email = f"test{self._user_id}@example.com"
            self.password = "test"
        
        # First get the login page to get the CSRF token
        response = self.client.get("/accounts/login/")
        if response.status_code != 200:
            raise StopUser("Failed to get login page")
            
        # Parse the CSRF token from the response
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
        
        # Store the CSRF token for future requests
        self.csrf_token = csrf_token
        
        # Set up CSRF token in headers for future requests
        self.client.headers.update({'X-CSRFToken': csrf_token})
        
        login_data = {
            'csrfmiddlewaretoken': csrf_token,
            'login': self.email,
            'password': self.password
        }
        
        response = self.client.post("/accounts/login/", data=login_data)
        if response.status_code != 200:
            raise StopUser(f"Failed to login for user {self.email}")

        if not self.is_staff:
            # Get team information by visiting the current team page
            response = self.client.get("/team/current/view/")
            if response.status_code != 200:
                raise StopUser("Failed to get team information")

            # Parse the team ID from the page content
            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                # Find the current team's menu link which has an ID of team-menu-link-{team_id}
                team_link = soup.find('a', id=lambda x: x and x.startswith('team-menu-link-'))
                if not team_link:
                    raise ValueError("Could not find team menu link")
                
                # Extract the team ID from the link ID (format: team-menu-link-{team_id})
                self.team_id = int(team_link['id'].split('-')[-1])
                print(f"Logged in as user {self.email} with team ID {self.team_id}")
            except (ValueError, AttributeError, IndexError) as e:
                raise StopUser(f"Failed to extract team ID from page content: {str(e)}")

    def _process_messages_loop(self):
        while not self._should_stop:
            try:
                event = next(self._sse_client)
                start_time = time.time()
                try:
                    # Try to parse the data as JSON
                    try:
                        data = json.loads(event.data)
                    except json.JSONDecodeError:
                        data = event.data
                    
                    # Call matching handlers
                    for pattern, handler in self._event_handlers:
                        if pattern.match(event.event):
                            handler(self, event.event, data)
                    
                    total_time = int((time.time() - start_time) * 1000)
                    events.request.fire(
                        request_type="SSE",
                        name=f"Message {event.event}",
                        response_time=total_time,
                        response_length=len(event.data),
                        response=event,
                        context=self.context(),
                        exception=None,
                    )
                    
                except Exception as e:
                    total_time = int((time.time() - start_time) * 1000)
                    events.request.fire(
                        request_type="SSE",
                        name=f"Message {event.event}",
                        response_time=total_time,
                        response_length=len(event.data) if hasattr(event, 'data') else 0,
                        response=event if hasattr(event, 'data') else None,
                        context=self.context(),
                        exception=e,
                    )
            except (StopIteration, TimeoutError):
                # Small sleep to prevent tight loop if no messages
                gevent.sleep(0.1)
                continue
            except Exception as e:
                # Handle errors, maybe reconnect if needed
                break
    
    def load_static_content(self, response):
        """
        Parse an HTML response for static content and load uncached files.
        Handles both regular static files and protected files.
        Also handles HTMX content loading via hx-get attributes.
        
        Args:
            response: The response object from a page request
        """
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get base URL for resolving relative paths
        base_url = response.url
        
        # Find all static content
        static_urls = set()
        
        # CSS files (both link tags and style imports)
        for css in soup.find_all('link', rel='stylesheet'):
            if css.get('href'):
                static_urls.add(urljoin(base_url, css['href']))
        
        # JavaScript files
        for script in soup.find_all('script', src=True):
            static_urls.add(urljoin(base_url, script['src']))
        
        # Images (including favicon)
        for img in soup.find_all('img', src=True):
            static_urls.add(urljoin(base_url, img['src']))
        for link in soup.find_all('link', rel='icon'):
            if link.get('href'):
                static_urls.add(urljoin(base_url, link['href']))
        
        # Load any uncached static content
        for url in static_urls:
            if url not in self.static_cache:
                self.client.get(url)
                self.static_cache.add(url)
        
        # Handle HTMX content loading
        for htmx_elem in soup.find_all(attrs={'hx-get': True}):
            if not htmx_elem.get('hx-trigger', '').startswith('load'):
                continue
            htmx_url = htmx_elem.get('hx-get')
            if htmx_url:
                # Convert relative HTMX URL to absolute
                absolute_htmx_url = urljoin(base_url, htmx_url)
                # Make the HTMX request
                htmx_response = self.client.get(absolute_htmx_url, headers={'HX-Request': 'true'})
                if htmx_response.status_code == 200:
                    # Recursively load static content from the HTMX response
                    self.load_static_content(htmx_response)
    
    def get_and_load_static(self, url: str) -> Optional[requests.Response]:
        """
        Make a GET request to the specified URL and load static content if successful.
        
        Args:
            url: The URL to request
            
        Returns:
            The response object if status code was 200, None otherwise
        """
        with self.client.get(url) as response:
            if response.status_code == 200:
                self.load_static_content(response)
                return response
        return None

    def connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """
        Establish an SSE connection to the specified URL.
        
        Args:
            url: The URL to connect to
            headers: Optional headers to include in the request
        """
        if self._connected:
            return
            
        start_time = time.time()
        try:
            if not headers:
                headers = {}
            
            # SSE requires text/event-stream
            headers['Accept'] = 'text/event-stream'
            
            # Copy all cookies from the client session
            self.session.cookies.update(self.client.cookies)
            
            # Format cookies as a string for the Cookie header
            cookie_dict = self.client.cookies.get_dict()
            cookie_str = '; '.join(f'{k}={v}' for k, v in cookie_dict.items())
            headers['Cookie'] = cookie_str
            
            # Add other important headers
            headers['X-CSRFToken'] = self.csrf_token
            headers['Referer'] = self.host
            
            # Create SSE connection with full URL
            full_url = urljoin(self.host, url.lstrip('/'))
            self._sse_client = sseclient.SSEClient(full_url, headers=headers)
            self._connected = True
            
            # Report successful connection
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="SSE",
                name=f"Connect {url}",
                response_time=total_time,
                response_length=0,
                response=None,
                context=self.context(),
                exception=None,
            )
            
            # Start background processing
            self._should_stop = False
            self._processing_greenlet = gevent.spawn(self._process_messages_loop)
            
        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="SSE",
                name=f"Connect {url}",
                response_time=total_time,
                response_length=0,
                response=None,
                context=self.context(),
                exception=e,
            )
            raise LocustError(f"Failed to connect to SSE: {e}")
    
    def disconnect(self) -> None:
        """Close the SSE connection if it exists."""
        if self._connected:
            self._should_stop = True
            if self._processing_greenlet:
                try:
                    gevent.kill(self._processing_greenlet)
                    self._processing_greenlet.join(timeout=1)
                except Exception:
                    pass
                self._processing_greenlet = None
            
            if self._sse_client:
                try:
                    # Only try to close if we have a response and it's not already closed
                    if hasattr(self._sse_client, 'resp') and not self._sse_client.resp.raw.closed:
                        self._sse_client.resp.raw.close()
                except Exception:
                    pass
                self._sse_client = None
            
            self._connected = False
    
    def on(self, event_pattern: str) -> Callable:
        """
        Decorator to register an event handler for SSE messages.
        Supports regex patterns for event matching.
        
        Args:
            event_pattern: Regex pattern to match event names
            
        Usage:
            @user.on('submission-.*')  # Matches any submission event
            def handle_submission(self, event, data):
                print(f"Received submission: {data}")
        """
        pattern = re.compile(event_pattern)
        
        def decorator(f: Callable) -> Callable:
            self._event_handlers.append((pattern, f))
            return f
        return decorator
    
    def __del__(self):
        """Ensure connection is closed when the user is destroyed."""
        self.disconnect()

class HuntPlayer(PuzzlehuntUser):
    """
    A locust user class that simulates a puzzle hunt player.
    Maintains SSE connection and simulates realistic puzzle solving patterns.
    """
    
    # Add wait time between tasks - random between 5 and 15 seconds
    wait_time = between(20, 60)
    
    # Puzzle solving behavior constants
    VIEWS_BEFORE_SUBMISSION = 5  # Number of views before attempting a submission
    VIEWS_BEFORE_HINT = 3  # Number of views before considering a hint
    SUBMISSIONS_BEFORE_SOLVE = 3  # Number of wrong submissions before solving
    HINT_REQUEST_CHANCE = 0.1  # Probability of requesting a hint when conditions are met
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solved_puzzles = set()
        self.available_puzzles = set()
        self.current_puzzle = None
        self.puzzle_views = 0
        self.submissions_made = 0
        self.current_page = None  # Track current page to manage SSE connections

        @self.on("submission-.*")
        def fetch_puzzle_page_sse(self, event, data):
            puzzle_id = event.split("-")[1]
            if self.current_page == "puzzle" and puzzle_id == self.current_puzzle:
                self.get_and_load_static(f"/puzzle/{self.current_puzzle}/view/")

        @self.on("huntUpdate")
        def fetch_hunt_page_sse(self, event, data):
            if self.current_page == "hunt":
                self.get_and_load_static(f"/hunt/current/view/")
    
    def _connect_sse_for_page(self, page_type):
        """Helper method to manage SSE connections based on page type"""
        # Disconnect from any existing SSE connection
        self.disconnect()
        
        # Connect to appropriate SSE endpoint based on page type
        if page_type == "hunt" or page_type == "puzzle":
            self.connect(f"/sse/team/{self.team_id}/")
        
        self.current_page = page_type

    @task(10)
    def view_hunt(self):
        """View the main hunt page and its static content"""
        # View the main hunt page
        response = self.get_and_load_static(f"/hunt/current/view/")
        if response:
            # Connect to SSE for hunt page
            self._connect_sse_for_page("hunt")
            
            # Parse the hunt page to extract available puzzles
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all puzzle links - they're in the format /puzzle/{id}/view/
            puzzle_links = soup.find_all('a', href=lambda h: h and h.startswith('/puzzle/') and h.endswith('/view/'))
            
            # Extract puzzle IDs into a set
            self.available_puzzles = {link['href'].split('/')[2] for link in puzzle_links}
    
    @task(50)
    def view_puzzle(self):
        """View a puzzle page and its static content"""
        # If no puzzles are available, view the hunt first to discover them
        if not self.available_puzzles:
            self.view_hunt()
            return
            
        # Select a puzzle if we don't have one currently
        if not self.current_puzzle:
            self._select_new_puzzle()
            self.submissions_made = 0
            self.puzzle_views = 0

        # View the puzzle page
        response = self.get_and_load_static(f"/puzzle/{self.current_puzzle}/view/")
        if not response or response.status_code != 200:
            self.current_puzzle = None
            return
            
        if self.current_puzzle in self.solved_puzzles:
            self.current_puzzle = None
            return

        # Connect to SSE for puzzle page
        self._connect_sse_for_page("puzzle")

        # Increment view count
        self.puzzle_views += 1
        
        # Check the team still has the ability to submit an answer
        soup = BeautifulSoup(response.text, 'html.parser')
        answer_form = soup.find('form', attrs={'hx-post': lambda x: x and 'submit' in x})
        input_field = answer_form.find('input', {'name': 'answer'})
        submit_button = answer_form.find('button', {'type': 'submit'})
        if not answer_form or (input_field and input_field.has_attr('readonly')) or (submit_button and submit_button.has_attr('disabled')):
            self.current_puzzle = None
            self.solved_puzzles.add(self.current_puzzle)
            return
        
        # Consider requesting a hint if:
        # 1. We've viewed the puzzle enough times
        # 2. We've made at least one wrong submission
        # 3. Random chance
        if (self.puzzle_views >= self.VIEWS_BEFORE_HINT and 
            self.submissions_made >= 1 and 
            random.random() < self.HINT_REQUEST_CHANCE):
            self.request_hint()
        
        # Consider making a submission if we've viewed the puzzle enough times
        if self.puzzle_views >= self.VIEWS_BEFORE_SUBMISSION:
            if self.submissions_made >= self.SUBMISSIONS_BEFORE_SOLVE:
                if self.submit_answer(is_correct=True):
                    self.solved_puzzles.add(self.current_puzzle)
                    self.current_puzzle = None
                    self.submissions_made += 1
            else:
                if self.submit_answer(is_correct=False):
                    self.submissions_made += 1
            self.puzzle_views = 0
    
    def _select_new_puzzle(self):
        """Helper method to select a new puzzle to work on"""
        # Try to select an unsolved puzzle first
        unsolved_puzzles = self.available_puzzles - self.solved_puzzles
        if unsolved_puzzles:
            self.current_puzzle = random.choice(list(unsolved_puzzles))
        else:
            # All puzzles solved, pick any puzzle
            self.current_puzzle = random.choice(list(self.available_puzzles))
    
    def submit_answer(self, is_correct: bool = False):
        """Submit an answer to the current puzzle"""
        if not self.current_puzzle:
            return False
        
        answer = self.current_puzzle if is_correct else f"WRONG{self.submissions_made}"
        
        # Get current CSRF token from cookies
        csrf_token = self.client.cookies.get('csrftoken')
        if not csrf_token:
            return False
        
        response = self.client.post(
            f"/puzzle/{self.current_puzzle}/submit/",
            data={
                'answer': answer,
                'csrfmiddlewaretoken': csrf_token
            },
            headers= {
                'X-CSRFToken': csrf_token,
                'Referer': f"{self.host}/puzzle/{self.current_puzzle}/view/"
            }
        )
        
        # Check if the response indicates rate limiting
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            error_p = soup.find('p', class_='help is-danger')
            return not (error_p and "You have been rate limited" in error_p.text)
        except Exception:
            return True

    def request_hint(self):
        """Request a hint for the current puzzle"""
        if not self.current_puzzle:
            return
            
        # Get current CSRF token from cookies
        csrf_token = self.client.cookies.get('csrftoken')
        if not csrf_token:
            return
            
        # Submit the hint request
        self.client.post(
            f"/puzzle/{self.current_puzzle}/hints/submit/",
            data={
                'hintText': f"Need help with puzzle {self.current_puzzle}",
                'csrfmiddlewaretoken': csrf_token
            },
            headers={
                'X-CSRFToken': csrf_token,
                'Referer': f"{self.host}/puzzle/{self.current_puzzle}/view/"
            }
        )
    
    @task(1)
    def view_leaderboard(self):
        """Periodically check the leaderboard"""
        self._connect_sse_for_page("leaderboard")
        self.get_and_load_static(f"/hunt/current/leaderboard/")
    
    @task(1)
    def view_updates(self):
        """Check for hunt updates"""
        self._connect_sse_for_page("updates")
        self.get_and_load_static(f"/hunt/current/updates/")

class StaffMember(PuzzlehuntUser):
    """
    A locust user class that simulates a staff member monitoring and managing the hunt.
    Maintains SSE connection and simulates realistic staff behavior patterns.
    """
    
    # Add wait time between tasks
    wait_time = between(30, 60)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_view = None
        self.unclaimed_hints = []  # Store list of unclaimed hint IDs
        self.is_staff = True
    def _connect_sse_for_page(self, page_type):
        """Helper method to manage SSE connections based on page type"""
        # Disconnect from any existing SSE connection
        self.disconnect()
        
        # Connect to appropriate SSE endpoint based on page type
        if page_type in ["feed", "hints"]:
            self.connect("/sse/staff/")
        
        self.current_view = page_type
    
    @task(1)
    def monitor_progress(self):
        """Monitor the progress page for an extended period"""

        # View the progress page
        response = self.get_and_load_static(f"/staff/hunt/current/progress/")
        if response and response.status_code == 200:
            # Connect to SSE for progress page
            self._connect_sse_for_page("progress")

            start_time = time.time()
            end_time = start_time + (5 * 60)
            
            while time.time() < end_time:
                # Fetch progress data
                self.client.get("/staff/hunt/current/progress_data/")
                
                # Calculate time until next interval or end, whichever is sooner
                time_remaining = end_time - time.time()
                sleep_time = min(60, time_remaining)
                
                if sleep_time > 0:
                    gevent.sleep(sleep_time)
    
    @task(1)
    def monitor_feed(self):
        """Monitor the feed page for an extended period"""
            
        # View the feed page
        response = self.get_and_load_static(f"/staff/hunt/current/feed/")
        if response and response.status_code == 200:
            # Connect to SSE for feed page
            self._connect_sse_for_page("feed")
            gevent.sleep(5 * 60)
    
    @task(1)
    def manage_hints(self):
        """Check and respond to hints"""

        # View hints page
        response = self.get_and_load_static(f"/staff/hunt/current/hints/")
        if not response or response.status_code != 200:
            return
            
        # Connect to SSE for hints page
        self._connect_sse_for_page("hints")
        
        # Load unclaimed hints page
        response = self.get_and_load_static(f"/staff/hunt/current/hints/?hint_status=unclaimed")
        if not response or response.status_code != 200:
            return
            
        # Parse the page for unclaimed hint IDs
        soup = BeautifulSoup(response.text, 'html.parser')
        self.unclaimed_hints = []  # Reset the list
        
        # Find all hint rows - all hints are unclaimed since we used the filter
        hint_rows = soup.find_all('div', class_='hint_row')
        for row in hint_rows:
            # Extract hint ID from the row ID (format: hint-row-{id})
            hint_id = row.get('id').split('-')[-1]
            self.unclaimed_hints.append(hint_id)
        
        # Process unclaimed hints
        while self.unclaimed_hints:
            hint_id = random.choice(self.unclaimed_hints)
            self.unclaimed_hints.remove(hint_id)
            
            # First claim the hint via the modal endpoint
            csrf_token = self.client.cookies.get('csrftoken')
            if not csrf_token:
                continue
                
            response = self.client.post(
                f"/staff/hint/{hint_id}/get_modal/",
                data={
                    'claim': 'true',
                    'csrfmiddlewaretoken': csrf_token
                },
                headers={
                    'HX-Request': 'true',
                    'HX-Target': '#staff-hint-modal-contents',
                    'X-CSRFToken': csrf_token,
                    'Referer': f"{self.host}/staff/hunt/current/hints/"
                }
            )
            
            if response.status_code != 200:
                continue
                
            # Wait 30 seconds before responding
            gevent.sleep(30)
            
            # Submit a response
            response = self.client.post(
                f"/staff/hint/{hint_id}/respond/",
                data={
                    'response': f"Here's a helpful hint for you! Responded by staff member {self.email}",
                    'csrfmiddlewaretoken': csrf_token
                },
                headers={
                    'HX-Request': 'true',
                    'HX-Target': f'#hint-row-{hint_id}',
                    'Referer': f"{self.host}/staff/hunt/current/hints/"
                }
            )
    
    @task(1)
    def view_charts(self):
        """Periodically check hunt statistics"""

        response = self.get_and_load_static(f"/staff/hunt/current/charts/")
        if response and response.status_code == 200:
            # Connect to SSE for charts page
            self._connect_sse_for_page("charts")
    
    @task(1)
    def view_puzzles_page(self):
        """View the puzzles page"""
        response = self.get_and_load_static(f"/staff/hunt/current/puzzles/")
        if response and response.status_code == 200:
            # Connect to SSE for puzzles page
            self._connect_sse_for_page("puzzles")


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Add custom stats table for rate limit tracking
    """
    normal_user_iterator = None
    staff_user_iterator = None
    if not isinstance(environment.runner, WorkerRunner):
        normal_user_iterator = iter(range(100))
        staff_user_iterator = iter(range(100))
    distributors["users"] = Distributor(environment, normal_user_iterator, "users")
    distributors["staff"] = Distributor(environment, staff_user_iterator, "staff")
    
    if environment.web_ui:
        # Add custom stats table for rate limits
        @environment.web_ui.app.route("/rate-limits")
        def rate_limits():
            rate_limit_stats = {}
            for user in environment.runner.user_classes:
                if hasattr(user, 'rate_limit_stats'):
                    rate_limit_stats[user.__name__] = user.rate_limit_stats
            return {
                "stats": rate_limit_stats,
                "errors": {},
                "failures": {},
            }

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Log final rate limit statistics when test stops
    """
    for user_class in environment.runner.user_classes:
        if hasattr(user_class, '_rate_limit_stats'):
            stats = user_class._rate_limit_stats['puzzle_submissions']
            logging.info(
                f"\nPuzzle Submission Rate Limit Stats for {user_class.__name__}:"
                f"\n  Total Submission Attempts: {stats['total_attempts']}"
                f"\n  Rate Limited Count: {stats['rate_limited_count']}"
                f"\n  Rate Limited Percentage: {(stats['rate_limited_count'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0:.2f}%"
                f"\n  Last Rate Limit Time: {stats['last_rate_limit']}"
                f"\n  Last Known Time Remaining: {stats['time_remaining']}"
            )
