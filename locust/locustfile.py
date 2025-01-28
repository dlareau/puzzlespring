import time
import json
import random
import string
from typing import Optional, Dict, Any, Callable
from urllib.parse import urljoin

import gevent
from locust import User, task, events
from locust.exception import LocustError, StopUser
import sseclient
import requests
from bs4 import BeautifulSoup

class PuzzlehuntUser(User):
    """
    Base locust user class that supports Server-Sent Events (SSE) connections
    and common puzzlehunt functionality like static content loading.
    """
    abstract = True  # This is a base class that should be inherited from
    
    # Class-level shared state for team management
    _available_teams = {}  # team_join_code -> (team_id, current_member_count)
    _teams_lock = gevent.lock.BoundedSemaphore(1)  # Lock for thread-safe team management
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self._sse_client = None
        self._connected = False
        self._event_handlers = {}
        self._processing_greenlet = None
        self._should_stop = False
        self.static_cache = set()  # Track which static files we've "cached"
        self.email = None
        self.password = None
        self.csrf_token = None
        self.team_id = None
        self.team_join_code = None
    
    def _create_test_user(self):
        """Create a unique test user for this load test instance"""
        
        # Generate unique credentials
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.email = f"test_{random_string}@example.com"
        self.password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # Get CSRF token first
        response = self.client.get("/accounts/signup/")
        self.csrf_token = response.cookies['csrftoken']
        
        # Create the user
        signup_data = {
            'csrfmiddlewaretoken': self.csrf_token,
            'email': self.email,
            'password1': self.password,
            'password2': self.password,
            'first_name': f"Test{random_string}",
            'last_name': "User",
            'display_name': f"TestUser_{random_string}"
        }
        
        response = self.client.post("/accounts/signup/", data=signup_data)
        if response.status_code != 200:
            raise StopUser(f"Failed to sign up for user {self.email}")
        
    def login(self):
        """Login the user with their credentials"""
        if not self.email or not self.password:
            self._create_test_user()
            
        login_data = {
            'csrfmiddlewaretoken': self.csrf_token,
            'login': self.email,
            'password': self.password
        }
        
        response = self.client.post("/accounts/login/", data=login_data)
        if response.status_code != 200:
            raise StopUser(f"Failed to login for user {self.email}")

    def create_or_join_team(self):
        """Create a new team or join an existing one"""
        join_code = None
        with self._teams_lock:
            for code, (team_id, count) in self._available_teams.items():
                if count < 4:  # Team has space
                    self._available_teams[code] = (team_id, count + 1)
                    join_code = code
                    self.team_id = team_id
                    break
        if join_code:
            response = self.client.get(f"/team/join/?code={join_code}")
            if response.status_code == 200:
                self.team_join_code = join_code
                return
            else:
                # Join failed, decrement the count
                with self._teams_lock:
                    team_id, count = self._available_teams[join_code]
                    self._available_teams[join_code] = (team_id, count - 1)
                raise StopUser(f"Failed to join team {join_code}")
        
        # No team to join or join failed, create a new one
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        team_data = {
            'csrfmiddlewaretoken': self.csrf_token,
            'name': f"TestTeam_{random_string}",
        }
        response = self.client.post("/team/create/", data=team_data)
        if response.status_code != 200:
            raise StopUser(f"Failed to create team {team_data['name']}")
        
        
        # Extract team ID and join code from the response
        soup = BeautifulSoup(response.text, 'html.parser')
        team_id = None
        team_form = soup.find('form', {'action': lambda x: x and '/team/' in x and '/update/' in x})
        if team_form:
            team_url = team_form['action']
            team_id = team_url.split('/')[2]  # Format is /team/{id}/update/
        
        join_code_label = soup.find('span', {'class': 'tag', 'text': 'Join Code'})
        if join_code_label:
            join_code_tag = join_code_label.find_next_sibling('span', {'class': 'tag', 'class': 'is-white'})
            if join_code_tag:
                join_code = join_code_tag.text.strip()

        if team_id is None or join_code is None:
            raise StopUser("Failed to extract team ID or join code")
        
        self.team_join_code = join_code
        self.team_id = team_id  
        with self._teams_lock:
            self._available_teams[join_code] = (team_id, 1)

    def on_start(self):
        """Called when a user starts running"""
        self.login()

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
                    
                    # Call the appropriate handler if it exists
                    if event.event in self._event_handlers:
                        self._event_handlers[event.event](self, data)
                    
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
        
        Args:
            response: The response object from a page request
        """
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all static content
        static_urls = set()
        
        # CSS files (both link tags and style imports)
        for css in soup.find_all('link', rel='stylesheet'):
            if css.get('href'):
                static_urls.add(css['href'])
        
        # JavaScript files
        for script in soup.find_all('script', src=True):
            static_urls.add(script['src'])
        
        # Images (including favicon)
        for img in soup.find_all('img', src=True):
            static_urls.add(img['src'])
        for link in soup.find_all('link', rel='icon'):
            if link.get('href'):
                static_urls.add(link['href'])
        
        # Load any uncached static content
        for url in static_urls:
            if url not in self.static_cache:
                self.client.get(url)
                self.static_cache.add(url)
    
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
            
            # Create SSE connection
            response = self.session.get(url, headers=headers, stream=True)
            self._sse_client = sseclient.SSEClient(response)
            self._connected = True
            
            # Report successful connection
            total_time = int((time.time() - start_time) * 1000)
            events.request.fire(
                request_type="SSE",
                name=f"Connect {url}",
                response_time=total_time,
                response_length=0,
                response=response,
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
                gevent.kill(self._processing_greenlet)
            self._sse_client.close()
            self._connected = False
            self._sse_client = None
            self._processing_greenlet = None
    
    def on(self, event_name: str) -> Callable:
        """
        Decorator to register an event handler for SSE messages.
        
        Args:
            event_name: The name of the event to handle
            
        Usage:
            @user.on('message')
            def handle_message(self, data):
                print(f"Received message: {data}")
        """
        def decorator(f: Callable) -> Callable:
            self._event_handlers[event_name] = f
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solved_puzzles = set()
        self.current_puzzle = None
        self.puzzle_views = 0
        self.submissions_made = 0
    
    def on_start(self):
        """Initial setup when user starts"""
        super().on_start()
        self.create_or_join_team()
        self.connect(f"/sse/team/{self.team_id}/")
        # TODO: Add event handlers for SSE events
    
    @task(1)
    def view_hunt(self):
        """View the main hunt page and its static content"""
        # View the main hunt page
        self.get_and_load_static(f"/hunt/current/view/")
    
    @task(3)
    def view_puzzle(self):
        """View a puzzle page and its static content"""
        if not self.current_puzzle:
            # Select a puzzle (this logic would be more sophisticated in reality)
            self.current_puzzle = "1"  # This would be dynamic
            
        # View the puzzle
        response = self.get_and_load_static(f"/puzzle/{self.current_puzzle}/view/")
        if response:
            self.puzzle_views += 1
            
            # After 5 views, consider making a submission
            if self.puzzle_views >= 5:
                self.submit_answer()
    
    def submit_answer(self):
        """Submit an answer to the current puzzle"""
        if not self.current_puzzle:
            return
            
        self.submissions_made += 1
        
        # Simulate correct answer after 3 wrong attempts
        is_correct = self.submissions_made % 3 == 0
        answer = "ANSWER" if is_correct else f"WRONG{self.submissions_made}"
        
        self.client.post(
            f"/puzzle/{self.current_puzzle}/submit/",
            json={"answer": answer}
        )
        
        if is_correct:
            self.solved_puzzles.add(self.current_puzzle)
            self.current_puzzle = None
            self.puzzle_views = 0
            self.submissions_made = 0
            
            # 1 in 3 chance of requesting a hint after solving
            if len(self.solved_puzzles) % 3 == 0:
                self.request_hint()
    
    def request_hint(self):
        """Request a hint for the just-solved puzzle"""
        if not self.current_puzzle:
            return
            
        self.client.post(
            f"/puzzle/{self.current_puzzle}/hints/submit/",
            json={"question": "Need help with the next step"}
        )
    
    @task(1)
    def view_leaderboard(self):
        """Periodically check the leaderboard"""
        self.get_and_load_static(f"/hunt/current/leaderboard/")
    
    @task(1)
    def view_updates(self):
        """Check for hunt updates"""
        self.get_and_load_static(f"/hunt/current/updates/")

class StaffMember(PuzzlehuntUser):
    """
    A locust user class that simulates a staff member monitoring and managing the hunt.
    Maintains SSE connection and simulates realistic staff behavior patterns.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_view = None
        self.view_start_time = None
    
    def on_start(self):
        """Initial setup when staff member starts"""
        # Login would go here in the future if needed
        self.connect_to_sse()
    
    def connect_to_sse(self):
        """Establish SSE connection for staff updates"""
        self.connect("/sse/staff/")
    
    @task(2)
    def monitor_progress(self):
        """Monitor the progress page for an extended period"""
        
        # If we're already viewing something, check if we should switch
        if self.current_view and time.time() - self.view_start_time < 300:  # 5 minutes
            return
            
        # View the progress page
        with self.client.get(f"/staff/hunt/current/progress/") as response:
            if response.status_code == 200:
                # Load any uncached static content
                static_files = [
                    "/static/staff/progress.css",
                    "/static/staff/progress.js"
                ]
                
                for static_file in static_files:
                    if static_file not in self.static_cache:
                        self.client.get(static_file)
                        self.static_cache.add(static_file)
                
                self.current_view = "progress"
                self.view_start_time = time.time()
    
    @task(2)
    def monitor_feed(self):
        """Monitor the feed page for an extended period"""
        
        # If we're already viewing something, check if we should switch
        if self.current_view and time.time() - self.view_start_time < 300:  # 5 minutes
            return
            
        # View the feed page
        with self.client.get(f"/staff/hunt/current/feed/") as response:
            if response.status_code == 200:
                # Load any uncached static content
                static_files = [
                    "/static/staff/feed.css",
                    "/static/staff/feed.js"
                ]
                
                for static_file in static_files:
                    if static_file not in self.static_cache:
                        self.client.get(static_file)
                        self.static_cache.add(static_file)
                
                self.current_view = "feed"
                self.view_start_time = time.time()
    
    @task(1)
    def manage_hints(self):
        """Check and respond to hints"""
        
        # View hints page
        with self.client.get(f"/staff/hunt/current/hints/") as response:
            if response.status_code == 200:
                # Simulate responding to an unclaimed hint
                # In reality, we'd parse the response to find actual hint IDs
                hint_id = 1  # This would be dynamic based on response
                
                # Claim the hint
                self.client.post(f"/staff/hint/{hint_id}/claim/")
                
                # Respond to the hint
                self.client.post(
                    f"/staff/hint/{hint_id}/respond/",
                    json={"response": "Here's a helpful hint!"}
                )
    
    @task(1)
    def view_charts(self):
        """Periodically check hunt statistics"""
        
        # If we're already viewing something, check if we should switch
        if self.current_view and time.time() - self.view_start_time < 300:  # 5 minutes
            return
            
        with self.client.get(f"/staff/hunt/current/charts/") as response:
            if response.status_code == 200:
                # Load any uncached static content
                static_files = [
                    "/static/staff/charts.css",
                    "/static/staff/charts.js"
                ]
                
                for static_file in static_files:
                    if static_file not in self.static_cache:
                        self.client.get(static_file)
                        self.static_cache.add(static_file)
