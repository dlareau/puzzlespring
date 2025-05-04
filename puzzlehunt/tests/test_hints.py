import datetime
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from bs4 import BeautifulSoup
from puzzlehunt.models import Hunt, Puzzle, User, CannedHint
from puzzlehunt.models import PuzzleStatus, Hint, Team

# Helper function to create common objects
def create_hunt_puzzle_team(is_public_hunt=True):
    now = timezone.now()
    start = now - datetime.timedelta(days=2) if is_public_hunt else now - datetime.timedelta(hours=1)
    end = now - datetime.timedelta(days=1) if is_public_hunt else now + datetime.timedelta(days=1)

    hunt = Hunt.objects.create(
        name="Test Hint Hunt",
        start_date=start,
        end_date=end,
        display_start_date=start,
        display_end_date=end,
        team_size_limit=4, 
    )
    puzzle = Puzzle.objects.create(
        id='thp1',
        hunt=hunt,
        name="Hint Test Puzzle",
        answer="ANSWER",
        order_number=1,
    )
    team = Team.objects.create(
        name="Test Hint Team",
        hunt=hunt 
    )
    return hunt, puzzle, team


class PublicHuntHintViewTests(TestCase):
    """Tests hint views when hunt.is_public == True."""

    def setUp(self):
        self.client = Client()
        self.hunt, self.puzzle, self.team = create_hunt_puzzle_team(is_public_hunt=True)
        self.hint_url = reverse("puzzlehunt:puzzle_hints_view", args=[self.puzzle.id])
        self.puzzle_url = reverse("puzzlehunt:puzzle_view", args=[self.puzzle.id])

    # Section 1.1: Hint Link/Button (Puzzle Infobox)

    def test_1_1_1_infobox_link_no_hints(self):
        """Test 1.1.1: Puzzle has no canned hints - link should not render."""
        response = self.client.get(self.puzzle_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'href="{self.hint_url}"')
        self.assertNotContains(response, ">View Hints</")

    def test_1_1_2_infobox_link_with_hints(self):
        """Test 1.1.2: Puzzle has canned hints - link should render."""
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Hint 1 text")
        response = self.client.get(self.puzzle_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        hint_link = soup.find('a', href=self.hint_url)
        self.assertIsNotNone(hint_link, f"Could not find link with href='{self.hint_url}'")
        self.assertIn("View Hints", hint_link.get_text(), "Link text does not contain 'View Hints'")

    # Section 1.2: Canned Hints Display (Hint Page)

    def test_1_2_1_hint_page_no_canned_hints(self):
        """Test 1.2.1: Hint page with no canned hints - section shouldn't render."""
        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<h2>Canned hints</h2>")
        self.assertNotContains(response, 'id="canned-hint-rows-outer"')

    def test_1_2_2_hint_page_with_canned_hints_initial(self):
        """Test 1.2.2: Hint page with canned hints - initial locked state."""
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Hint 1 text")
        CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Hint 2 text")
        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        heading = soup.find('h2', class_='mb-2 is-size-4')
        self.assertIsNotNone(heading)
        bold_text = heading.find('b')
        self.assertIsNotNone(bold_text)
        self.assertIn("Canned hints", bold_text.get_text(strip=True))

        outer_div = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(outer_div)
        hint_boxes = outer_div.find_all('div', class_='box', recursive=False)
        self.assertEqual(len(hint_boxes), 2)

        canned_outer_div = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(canned_outer_div)
        self.assertIn("Canned Hint #1", canned_outer_div.get_text())
        self.assertIn("Canned Hint #2", canned_outer_div.get_text())
        self.assertEqual(len(canned_outer_div.select('.fa-lock')), 2)
        reveal_buttons = canned_outer_div.find_all('button', string=lambda t: 'Reveal Hint' in t)
        self.assertEqual(len(reveal_buttons), 2)

    def test_1_2_2_hint_page_reveal_one_canned_hint(self):
        """Test 1.2.2 Interaction: Reveal one canned hint (Check initial state)."""
        h1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Hint 1 text")
        h2 = CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Hint 2 text")

        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        outer_div = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(outer_div)
        hint_boxes = outer_div.find_all('div', class_='box', recursive=False)
        self.assertEqual(len(hint_boxes), 2)

        hint1_box = hint_boxes[0]
        self.assertTrue(hint1_box.find(class_='fa-lock'))
        self.assertIn("revealed: false", hint1_box.get('x-data', ''))
        reveal_button_1 = hint1_box.find('button', string=lambda t: 'Reveal Hint' in t)
        self.assertIsNotNone(reveal_button_1)
        revealed_div = hint1_box.find('div', attrs={'x-show': 'revealed'})
        self.assertIsNotNone(revealed_div)
        self.assertIn(h1.text, revealed_div.get_text())

        hint2_box = hint_boxes[1]
        self.assertTrue(hint2_box.find(class_='fa-lock'))
        self.assertIn("revealed: false", hint2_box.get('x-data', ''))
        revealed_div_2 = hint2_box.find('div', attrs={'x-show': 'revealed'})
        self.assertIsNotNone(revealed_div_2)
        self.assertIn(h2.text, revealed_div_2.get_text())

    def test_1_2_2_hint_page_reveal_all_canned_hints(self):
        """Test 1.2.2 Interaction: Reveal all canned hints (Check initial state)."""
        h1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Hint 1 text")
        h2 = CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Hint 2 text")

        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        outer_div = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(outer_div)
        hint_boxes = outer_div.find_all('div', class_='box', recursive=False)
        self.assertEqual(len(hint_boxes), 2)

        reveal_button_1 = hint_boxes[0].find('button', string=lambda t: 'Reveal Hint' in t)
        reveal_button_2 = hint_boxes[1].find('button', string=lambda t: 'Reveal Hint' in t)
        self.assertIsNotNone(reveal_button_1)
        self.assertIsNotNone(reveal_button_2)

    # Section 1.3: Custom Hints Display (Hint Page)

    def test_1_3_1_hint_page_no_custom_hints(self):
        """Test 1.3.1: Hint page, public view, no prior custom hints."""
        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<h2>Previous Custom Hints</h2>")
        self.assertNotContains(response, 'id="custom-hint-rows-outer"')
        self.assertNotContains(response, "<form")

    def test_1_3_2_hint_page_with_custom_hints(self):
        """Test 1.3.2: Hint page, public view, should NOT show prior custom hints."""
        unlock_time = timezone.now() - datetime.timedelta(hours=6)
        PuzzleStatus.objects.create(
            puzzle=self.puzzle,
            team=self.team,
            unlock_time=unlock_time
        )

        Hint.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            request="Need help please",
            response="Try looking at the image.",
            request_time=unlock_time + datetime.timedelta(hours=1),
            response_time=unlock_time + datetime.timedelta(hours=2),
            last_modified_time=unlock_time + datetime.timedelta(hours=2)
        )
        response = self.client.get(self.hint_url)
        self.assertEqual(response.status_code, 200)
        # Public view should NOT show custom hints section or form, even if they exist
        self.assertNotContains(response, "<h2>Previous Custom Hints</h2>")
        self.assertNotContains(response, 'id="custom-hint-rows-outer"')
        self.assertNotContains(response, "<form")
        self.assertNotContains(response, "Need help please")
        self.assertNotContains(response, "Try looking at the image.") 

# Section 2 Tests (Active Hunt)

class HintActiveHuntViewTests(TestCase):
    """Tests hint functionality during an active hunt (hunt.is_public=False)."""

    @classmethod
    def setUpTestData(cls):
        # Create a hunt that is currently active
        now = timezone.now()
        cls.hunt = Hunt.objects.create(
            name="Active Hint Test Hunt",
            team_size_limit=4,
            start_date=now - datetime.timedelta(days=1),
            end_date=now + datetime.timedelta(days=1), # Hunt is ongoing
            display_start_date=now - datetime.timedelta(days=1),
            display_end_date=now + datetime.timedelta(days=1),
            location="Test Location",
            is_current_hunt=False, # Avoid conflicts with potential real current hunt
            hint_lockout=60 # 60 minutes lockout
            # Default hint policies: GLOBAL_ONLY, CANNED_FIRST, PUZZLE_PRIORITY
        )
        cls.user = User.objects.create_user(email="hintactivetester@example.com", password="password")
        cls.team = Team.objects.create(
            name="Hint Active Test Team",
            hunt=cls.hunt,
            join_code="ACTIVEHINT"
        )
        cls.team.members.add(cls.user)
        cls.puzzle = Puzzle.objects.create(
            id="HINTACTV",
            hunt=cls.hunt,
            name="Active Hint Test Puzzle",
            order_number=1,
            answer="ANSWER"
        )
        cls.hints_url = reverse("puzzlehunt:puzzle_hints_view", args=[cls.puzzle.pk])
        cls.puzzle_url = reverse("puzzlehunt:puzzle_view", args=[cls.puzzle.pk])

    def setUp(self):
        self.client.force_login(self.user)
        # Ensure team/status hints are reset before each test
        self.team.refresh_from_db()
        self.team.num_available_hints = 0
        self.team.num_total_hints_earned = 0
        self.team.save()
        PuzzleStatus.objects.filter(team=self.team, puzzle=self.puzzle).update(
            num_available_hints=0,
            num_total_hints_earned=0
        )


    # ============================================
    # 2.1: Page Access Control
    # ============================================

    def test_2_1_1_no_status_denies_access(self):
        """2.1.1: Team has no PuzzleStatus -> Access denied (renders error page)."""
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200, "Access denied should render the error page with status 200.")
        self.assertContains(response, "You do not have access to this page.", msg_prefix="Error page content missing or wrong.")

    def test_2_1_2_within_lockout_denies_access(self):
        """2.1.2: Team unlocked puzzle within hunt.hint_lockout -> Access denied (renders error page)."""
        now = timezone.now()
        PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout - 10) # Unlocked 10 mins *before* lockout ends
        )
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200, "Access denied should render the error page with status 200.")
        self.assertContains(response, "You do not have access to this page.", msg_prefix="Error page content missing or wrong.")

    def test_2_1_3_outside_lockout_no_hints_available_or_used_denies_access(self):
        """2.1.3: Outside lockout, no available hints (global/puzzle), no prior hints used -> Access denied (renders error page)."""
        now = timezone.now()
        PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        self.team.num_available_hints = 0
        self.team.save()

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200, "Access denied should render the error page with status 200.")
        self.assertContains(response, "You do not have access to this page.", msg_prefix="Error page content missing or wrong.")

    def test_2_1_4_outside_lockout_has_available_custom_grants_access(self):
        """2.1.4: Outside lockout, has available custom hints -> Access granted."""
        now = timezone.now()
        status = PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.save()
        self.team.num_available_hints = 1
        self.team.save()

        self.assertTrue(self.team.hints_open_for_puzzle(self.puzzle))
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.puzzle.name)

    def test_2_1_5_outside_lockout_has_available_canned_grants_access(self):
        """2.1.5: Outside lockout, has available canned hints -> Access granted."""
        now = timezone.now()
        status = PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned Hint 1")
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.save()
        self.team.num_available_hints = 1
        self.team.save()

        self.assertTrue(self.team.hints_open_for_puzzle(self.puzzle))
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.puzzle.name)

    def test_2_1_6_outside_lockout_no_available_hints_but_used_grants_access(self):
        """2.1.6: Outside lockout, no currently available hints, but previously used a hint -> Access granted."""
        now = timezone.now()
        status = PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        # Create prior hint (needs last_modified_time)
        Hint.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            request="Test request",
            request_time=now - datetime.timedelta(minutes=10),
            response="Test response",
            response_time=now - datetime.timedelta(minutes=5),
            last_modified_time=now - datetime.timedelta(minutes=5)
        )
        # Creating hint decremented count, so reset to 0
        self.team.refresh_from_db()
        self.team.num_available_hints = 0
        self.team.save()
        status.refresh_from_db()
        status.num_available_hints = 0
        status.save()

        self.assertTrue(self.team.hints_open_for_puzzle(self.puzzle))
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.puzzle.name)

    # ============================================
    # 2.2: Hint Link/Button (Puzzle Infobox)
    # ============================================

    def test_2_2_1_cannot_access_hints_no_link_on_infobox(self):
        """2.2.1: Team cannot access hints (outside lockout, 0 avail/used hints) -> Link/button NOT rendered."""
        now = timezone.now()
        status = PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        self.team.num_available_hints = 0
        self.team.save()
        status.num_available_hints = 0
        status.save()

        self.assertTrue(self.puzzle.check_access(self.user))
        self.assertFalse(self.team.hints_open_for_puzzle(self.puzzle))

        response = self.client.get(self.puzzle_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        infobox = soup.find(id='puzzle-infobox')
        self.assertIsNotNone(infobox)

        hints_link = infobox.find('a', href=self.hints_url)
        self.assertIsNone(hints_link)

    def test_2_2_2_can_access_hints_link_present_on_infobox(self):
        """2.2.2: Team can access hints -> Link/button IS rendered with correct text."""
        now = timezone.now()
        status = PuzzleStatus.objects.create(
            team=self.team,
            puzzle=self.puzzle,
            unlock_time=now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
        )
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.save()
        self.team.num_available_hints = 1
        self.team.save()

        response = self.client.get(self.puzzle_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        infobox = soup.find(id='puzzle-infobox')
        self.assertIsNotNone(infobox)
        hints_link = infobox.find('a', href=self.hints_url)
        self.assertIsNotNone(hints_link)
        self.assertIn("View/Request Hints", hints_link.get_text(strip=True))

    # ============================================
    # 2.3: Canned Hints Display & Interaction
    # ============================================

    def _setup_access_granted(self):
        """Helper to grant hint page access for subsequent tests."""
        now = timezone.now()
        # Ensure status exists and is outside lockout
        status, created = PuzzleStatus.objects.get_or_create(
            team=self.team,
            puzzle=self.puzzle,
            defaults={'unlock_time': now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)}
        )
        if not created and status.unlock_time > now - datetime.timedelta(minutes=self.hunt.hint_lockout):
            status.unlock_time = now - datetime.timedelta(minutes=self.hunt.hint_lockout + 10)
            status.save()
        
        # Grant at least one hint (global pool) to ensure access, 
        # individual tests can override counts later.
        self.team.refresh_from_db()
        if self.team.num_available_hints <= 0:
             self.team.num_available_hints = 1
             self.team.save()
        return status

    def test_2_3_1_no_canned_hints_section_not_rendered(self):
        """2.3.1: Puzzle has no canned hints -> Canned hint section not rendered."""
        self._setup_access_granted()
        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        canned_section = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNone(canned_section)

    def test_2_3_2_multiple_canned_hints_some_used_renders_correctly(self):
        """2.3.2: Puzzle has canned hints, team used some -> Renders used, next locked, subsequent greyed out."""
        status = self._setup_access_granted()
        now = timezone.now()
        ch1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned 1 Text")
        ch2 = CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Canned 2 Text")
        ch3 = CannedHint.objects.create(puzzle=self.puzzle, order=3, text="Canned 3 Text")

        # Use the first hint
        used_hint = Hint.objects.create(
            team=self.team, puzzle=self.puzzle, canned_hint=ch1,
            request_time=now - datetime.timedelta(minutes=5),
            response="Revealed Canned Hint", response_time=now - datetime.timedelta(minutes=5),
            last_modified_time=now - datetime.timedelta(minutes=5)
        )

        # Configure hunt policy
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.PUZZLE_PRIORITY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        
        # Ensure hints are available after potential decrement by hint creation
        status.refresh_from_db()
        status.num_available_hints = 1 # Puzzle pool
        status.save()
        self.team.num_available_hints = 1 # Global pool
        self.team.save()

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        canned_section = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(canned_section)
        title = canned_section.find_previous_sibling('h2')
        self.assertIsNotNone(title)
        self.assertIn("Canned hints", title.get_text(strip=True))

        used_hint_row = canned_section.find('div', id=f'hint-row-{used_hint.id}')
        self.assertIsNotNone(used_hint_row)
        self.assertIn(ch1.text, used_hint_row.get_text())
        self.assertIn(f"Canned Hint #{ch1.order}", used_hint_row.get_text())

        locked_boxes = canned_section.find_all('div', class_='box', recursive=False)
        next_hint_box = None
        subsequent_hint_box = None
        for box in locked_boxes:
            if f"Canned Hint #{ch2.order}" in box.get_text():
                next_hint_box = box
            elif f"Canned Hint #{ch3.order}" in box.get_text():
                subsequent_hint_box = box
        
        # Check next hint (ch2)
        self.assertIsNotNone(next_hint_box)
        self.assertNotIn('has-background-grey-lighter', next_hint_box.get('class', []))
        self.assertIsNotNone(next_hint_box.find('i', class_='fa-lock'))
        unlock_form = next_hint_box.find('form')
        self.assertIsNotNone(unlock_form)
        unlock_button = unlock_form.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button)
        self.assertEqual(unlock_button.get_text(strip=True), "Unlock Hint")
        self.assertNotIn('disabled', unlock_button.attrs)

        # Check subsequent hint (ch3)
        self.assertIsNotNone(subsequent_hint_box)
        self.assertIn('has-background-grey-lighter', subsequent_hint_box.get('class', []))
        self.assertIsNotNone(subsequent_hint_box.find('i', class_='fa-lock'))
        unlock_form_subsequent = subsequent_hint_box.find('form')
        self.assertIsNotNone(unlock_form_subsequent)
        unlock_button_subsequent = unlock_form_subsequent.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button_subsequent)
        self.assertEqual(unlock_button_subsequent.get_text(strip=True), "Unlock Hint")
        self.assertIn('disabled', unlock_button_subsequent.attrs)

    def test_2_3_3_unlock_button_disabled_for_non_next_hint(self):
        """2.3.3: 'Unlock Hint' button is disabled for hints after the next available one."""
        status = self._setup_access_granted()
        ch1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned 1 Text")
        ch2 = CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Canned 2 Text")
        
        self.team.num_available_hints = 1 # Ensure hints available
        self.team.save()

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        canned_section = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(canned_section)

        locked_boxes = canned_section.find_all('div', class_='box', recursive=False)
        ch1_box = None
        ch2_box = None
        for box in locked_boxes:
             if f"Canned Hint #{ch1.order}" in box.get_text():
                ch1_box = box
             elif f"Canned Hint #{ch2.order}" in box.get_text():
                ch2_box = box

        # Check ch2 (non-next) button is disabled
        self.assertIsNotNone(ch2_box)
        unlock_form_ch2 = ch2_box.find('form')
        self.assertIsNotNone(unlock_form_ch2)
        unlock_button_ch2 = unlock_form_ch2.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button_ch2)
        self.assertIn('disabled', unlock_button_ch2.attrs)

        # Check ch1 (next) button is enabled
        self.assertIsNotNone(ch1_box)
        unlock_form_ch1 = ch1_box.find('form')
        self.assertIsNotNone(unlock_form_ch1)
        unlock_button_ch1 = unlock_form_ch1.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button_ch1)
        self.assertNotIn('disabled', unlock_button_ch1.attrs)

    def test_2_3_4_unlock_button_disabled_when_no_canned_requests_available(self):
        """2.3.4: 'Unlock Hint' button on the *next* hint is disabled if no canned requests are available."""
        status = self._setup_access_granted()
        ch1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned 1 Text")

        # Ensure NO hints available
        self.team.num_available_hints = 0
        self.team.save()
        status.num_available_hints = 0
        status.save()

        # Create a dummy used hint to maintain access grant condition 2.1.6
        self.team.num_available_hints = 1 # Give hint first
        self.team.save()
        Hint.objects.create(
            team=self.team, puzzle=self.puzzle, request="Dummy", 
            request_time=timezone.now(),
            last_modified_time=timezone.now()
        )
        self.team.refresh_from_db() # Creation consumed the hint
        self.assertEqual(self.team.num_available_hints, 0)
        status.refresh_from_db()
        self.assertEqual(status.num_available_hints, 0)

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        canned_section = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(canned_section)

        ch1_box = None
        locked_boxes = canned_section.find_all('div', class_='box', recursive=False)
        for box in locked_boxes:
             if f"Canned Hint #{ch1.order}" in box.get_text():
                ch1_box = box
                break
        self.assertIsNotNone(ch1_box)
        unlock_form_ch1 = ch1_box.find('form')
        self.assertIsNotNone(unlock_form_ch1)
        unlock_button = unlock_form_ch1.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button)
        self.assertIn('disabled', unlock_button.attrs)

    def test_2_3_5_unlock_button_enabled_when_canned_requests_available(self):
        """2.3.5: 'Unlock Hint' button on the *next* hint is enabled if canned requests available."""
        status = self._setup_access_granted()
        ch1 = CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned 1 Text")

        self.team.num_available_hints = 1 # Ensure hints ARE available
        self.team.save()

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')
        canned_section = soup.find('div', id='canned-hint-rows-outer')
        self.assertIsNotNone(canned_section)

        ch1_box = None
        locked_boxes = canned_section.find_all('div', class_='box', recursive=False)
        for box in locked_boxes:
             if f"Canned Hint #{ch1.order}" in box.get_text():
                ch1_box = box
                break
        self.assertIsNotNone(ch1_box)
        unlock_form_ch1 = ch1_box.find('form')
        self.assertIsNotNone(unlock_form_ch1)
        unlock_button = unlock_form_ch1.find('button', class_='is-primary')
        self.assertIsNotNone(unlock_button)
        self.assertNotIn('disabled', unlock_button.attrs)

    # ============================================
    # 2.4: Custom Hint Form Display & Interaction
    # ============================================

    def test_2_4_1_canned_only_policy_no_custom_section(self):
        """2.4.1: Hunt policy is CANNED_ONLY -> Custom hint section is not rendered."""
        self._setup_access_granted()
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.CANNED_ONLY
        self.hunt.save()
        self.team.refresh_from_db() # Ensure team sees new policy

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        custom_form = soup.find('form', id='hint-submit-form')
        self.assertIsNone(custom_form)
        custom_title = soup.find('h2', string=lambda t: 'Submit a new hint request' in t if t else False)
        self.assertIsNone(custom_title)

    def test_2_4_2_no_available_custom_and_no_prior_no_custom_section(self):
        """2.4.2: Allows custom hints, but team has 0 available and 0 prior -> Custom section not rendered."""
        status = self._setup_access_granted()
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.HINT_TYPE_SPLIT
        self.hunt.save()
        self.team.refresh_from_db()

        self.team.num_available_hints = 0 # Global pool = 0 -> Custom = 0
        self.team.save()
        status.num_available_hints = 1 # Puzzle pool = 1 -> Canned = 1
        status.save()
        status.refresh_from_db()

        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned 1 Text")
        # Verify access granted, custom = 0, canned = 1
        self.assertTrue(self.team.hints_open_for_puzzle(self.puzzle))
        self.assertEqual(status.num_custom_hint_requests_available, 0)
        self.assertEqual(self.team.num_custom_hint_requests_available(status), 0)
        self.assertEqual(status.num_canned_hint_requests_available, 1)
        self.assertEqual(self.team.num_canned_hint_requests_available(status), 1)

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        custom_form = soup.find('form', id='hint-submit-form')
        self.assertIsNone(custom_form)
        # Check outer box is also absent
        outer_box = soup.find('div', id='custom-hint-rows-outer')
        if outer_box:
            outer_box = outer_box.find_parent('div', class_='box')
        self.assertIsNone(outer_box)

    def test_2_4_3_prior_custom_but_no_available_shows_list_not_form(self):
        """2.4.3: Has prior custom hints but 0 available -> Shows list and title, but not form."""
        status = self._setup_access_granted()
        now = timezone.now()
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        # Make sure hint creation doesn't affect pool we care about (set to BOTH/SPLIT)
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.HINT_TYPE_SPLIT
        self.hunt.save()
        self.team.refresh_from_db()

        # Create a prior custom hint
        self.team.num_available_hints = 1 # Give global hint first
        self.team.save()
        prior_hint = Hint.objects.create(
            team=self.team, puzzle=self.puzzle, request="Prior custom request",
            request_time=now - datetime.timedelta(days=1), response="Staff response", response_time=now-datetime.timedelta(hours=1),
            last_modified_time=now-datetime.timedelta(hours=1)
        )
        self.team.refresh_from_db() # Hint creation consumed global hint
        self.assertEqual(self.team.num_available_hints, 0)

        # Ensure puzzle pool has 0 hints too
        status.num_available_hints = 0
        status.save()
        status.refresh_from_db()
        self.assertEqual(status.num_custom_hint_requests_available, 0)

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        custom_title = soup.find('h2', string=lambda t: 'Submit a new hint request' in t if t else False)
        self.assertIsNotNone(custom_title)

        custom_list = soup.find('div', id='custom-hint-rows-outer')
        self.assertIsNotNone(custom_list)
        self.assertIn(prior_hint.request, custom_list.get_text())
        self.assertIn(prior_hint.response, custom_list.get_text())

        custom_form = soup.find('form', id='hint-submit-form')
        self.assertIsNotNone(custom_form, "Custom hint form SHOULD be present when prior hints exist, even if none available.")
        
        # Check that the submit button exists, although it might be disabled by Alpine.js
        submit_button = custom_form.find('button', id='hint-submit-button')
        self.assertIsNotNone(submit_button, "Submit button should exist in the form.")

    def test_2_4_4_available_custom_hints_shows_form_and_list(self):
        """2.4.4: Has available custom requests -> Shows title, form, list (and button attributes)."""
        status = self._setup_access_granted()
        now = timezone.now()
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS # Use separate pools
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.HINT_TYPE_SPLIT
        self.hunt.save()
        self.team.refresh_from_db()

        # Create a prior custom hint (uses global pool)
        self.team.num_available_hints = 1 # Give hint first
        self.team.save()
        prior_hint = Hint.objects.create(
            team=self.team, puzzle=self.puzzle, request="Prior request again",
            request_time=now - datetime.timedelta(days=1),
            last_modified_time=now - datetime.timedelta(days=1)
        )
        self.team.refresh_from_db() # Hint creation consumed global hint
        self.assertEqual(self.team.num_available_hints, 0)

        # Now ensure custom hints ARE available (give back global hint)
        self.team.num_available_hints = 1
        self.team.save()
        status.num_available_hints = 0 # Puzzle pool (for canned) remains 0
        status.save()
        status.refresh_from_db()
        self.assertEqual(status.num_custom_hint_requests_available, 1)

        response = self.client.get(self.hints_url)
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, 'html.parser')

        custom_title = soup.find('h2', string=lambda t: 'Submit a new hint request' in t if t else False)
        self.assertIsNotNone(custom_title)

        custom_form = soup.find('form', id='hint-submit-form')
        self.assertIsNotNone(custom_form)

        textarea = custom_form.find('textarea', id='hint-request-text')
        self.assertIsNotNone(textarea)
        submit_button = custom_form.find('button', id='hint-submit-button')
        self.assertIsNotNone(submit_button)
        self.assertEqual(submit_button.get_text(strip=True), "Submit")

        self.assertIn('x-bind:disabled', submit_button.attrs)
        self.assertEqual(submit_button.attrs['x-bind:disabled'], "hintText==''")

        custom_list = soup.find('div', id='custom-hint-rows-outer')
        self.assertIsNotNone(custom_list)
        self.assertIn(prior_hint.request, custom_list.get_text())

    # ============================================
    # 2.5: Hint Count Display
    # ============================================
    def _check_hint_count_text(self, soup, expected_canned_text, expected_custom_text):
        """Helper to check hint count text in both sections"""
        canned_count_p = soup.select_one('#canned-hint-rows-outer > p.mb-2')
        if expected_canned_text is not None:
            self.assertIsNotNone(canned_count_p, "Canned count <p> tag not found")
            actual_canned_text = canned_count_p.get_text(separator=" ", strip=True)
            self.assertIn(expected_canned_text, actual_canned_text, f"Expected '{expected_canned_text}' in canned count")
        else:
            # If expected text is None, the tag should exist but be empty.
            self.assertIsNotNone(canned_count_p, "Canned count <p> tag should exist even if empty.")
            self.assertEqual(canned_count_p.get_text(strip=True), "", "Canned count <p> tag should be empty when expected text is None.")

        custom_count_p = None
        custom_section_box = soup.find('form', id='hint-submit-form')
        if custom_section_box:
            custom_section_box = custom_section_box.find_parent('div', class_='box')
        else:
             list_outer = soup.find('div', id='custom-hint-rows-outer')
             if list_outer:
                  parent_box = list_outer.find_parent('div', class_='box')
                  if parent_box and parent_box.find('h3', string=lambda t: 'Previous' in t if t else False):
                      custom_section_box = parent_box

        if custom_section_box:
            custom_count_p = custom_section_box.find('p', class_='mb-2', recursive=False)

        if expected_custom_text is not None:
            self.assertIsNotNone(custom_count_p, "Custom count <p> tag not found")
            actual_custom_text = custom_count_p.get_text(separator=" ", strip=True)
            self.assertIn(expected_custom_text, actual_custom_text, f"Expected '{expected_custom_text}' in custom count")
        else:
             if custom_section_box:
                 # If expected custom text is None, the <p> tag itself might not exist 
                 # if the form isn't rendered (depends on template structure)
                 # Let's just assert the section box is present but the count <p> is absent
                 self.assertIsNotNone(custom_section_box, "Custom section box should exist if expected text is None but section might render")
                 self.assertIsNone(custom_count_p, "Custom count <p> tag should not exist if expected_custom_text is None")

    def test_2_5_1_various_pool_allocations(self):
        """2.5.1: Test various hint pool/allocation combinations display correctly."""
        status = self._setup_access_granted()
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned")

        # Case A: GLOBAL_ONLY (Default setup from setUpTestData)
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 3
        self.team.save()
        status.num_available_hints = 0
        status.save()
        status.refresh_from_db()
        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self._check_hint_count_text(soup, "3 hint requests available", "3 hint requests available")

        # Case B: PUZZLE_ONLY
        self.hunt.hint_pool_type = Hunt.HintPoolType.PUZZLE_ONLY
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 0
        self.team.save()
        status.num_available_hints = 2
        status.save()
        status.refresh_from_db()
        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        CannedHint.objects.create(puzzle=self.puzzle, order=2, text="Canned 2")
        self.assertEqual(status.num_canned_hint_requests_available, 2)
        self.assertEqual(status.num_custom_hint_requests_available, 2)
        self._check_hint_count_text(soup, "2 hint requests available", "2 hint requests available")

        # Case C: BOTH_POOLS, PUZZLE_PRIORITY
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.PUZZLE_PRIORITY
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 3 # Global
        self.team.save()
        status.num_available_hints = 2 # Puzzle
        status.save()
        status.refresh_from_db()
        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        expected_text = "3 global hint requests available 2 puzzle-specific hint requests available"
        self._check_hint_count_text(soup, expected_text, expected_text)

        # Case D: BOTH_POOLS, HINT_TYPE_SPLIT
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.HINT_TYPE_SPLIT
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 3 # Global (for custom)
        self.team.save()
        status.num_available_hints = 2 # Puzzle (for canned)
        status.save()
        status.refresh_from_db()
        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Expected: Canned count <p> is empty, Custom count shows 3 (global)
        self._check_hint_count_text(soup, None, "3 hint requests available")

    def test_2_5_2_zero_available(self):
        """2.5.2: Display with 0 available hints shows correct text."""
        status = self._setup_access_granted()
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned")
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        
        self.team.num_available_hints = 0
        self.team.save()
        status.num_available_hints = 0
        status.save()
        
        self.team.num_available_hints = 1 # Give hint first
        self.team.save()
        Hint.objects.create(team=self.team, puzzle=self.puzzle, request="Dummy", 
                            request_time=timezone.now(),
                            last_modified_time=timezone.now()
                            )
        self.team.refresh_from_db()
        self.assertEqual(self.team.num_available_hints, 0)
        status.refresh_from_db()
        self.assertEqual(status.num_available_hints, 0)

        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self._check_hint_count_text(soup, "0 hint requests available", "0 hint requests available")

    def test_2_5_3_one_available(self):
        """2.5.3: Display with 1 available hint shows correct singular text."""
        status = self._setup_access_granted()
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned")
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 1
        self.team.save()
        status.num_available_hints = 0
        status.save()
        status.refresh_from_db()

        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self._check_hint_count_text(soup, "1 hint request available", "1 hint request available")

    def test_2_5_4_multiple_available(self):
        """2.5.4: Display with multiple available hints shows correct plural text."""
        status = self._setup_access_granted()
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned")
        self.hunt.hint_pool_type = Hunt.HintPoolType.GLOBAL_ONLY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 5
        self.team.save()
        status.num_available_hints = 0
        status.save()
        status.refresh_from_db()

        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self._check_hint_count_text(soup, "5 hint requests available", "5 hint requests available")

    def test_2_5_5_both_pools_puzz_allocation_shows_both_counts(self):
        """2.5.5: BOTH pools + PUZZ allocation shows both global and puzzle counts correctly."""
        status = self._setup_access_granted()
        CannedHint.objects.create(puzzle=self.puzzle, order=1, text="Canned")
        self.hunt.hint_pool_type = Hunt.HintPoolType.BOTH_POOLS
        self.hunt.hint_pool_allocation = Hunt.HintPoolAllocation.PUZZLE_PRIORITY
        self.hunt.canned_hint_policy = Hunt.CannedHintPolicy.MIXED
        self.hunt.save()
        self.team.refresh_from_db()
        self.team.num_available_hints = 3 # Global
        self.team.save()
        status.num_available_hints = 1 # Puzzle (Singular)
        status.save()
        status.refresh_from_db()

        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        expected_text = "3 global hint requests available 1 puzzle-specific hint request available"
        self._check_hint_count_text(soup, expected_text, expected_text)

        # Test plural puzzle count too
        status.num_available_hints = 4 # Puzzle (Plural)
        status.save()
        status.refresh_from_db()
        response = self.client.get(self.hints_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        expected_text_plural = "3 global hint requests available 4 puzzle-specific hint requests available"
        self._check_hint_count_text(soup, expected_text_plural, expected_text_plural)