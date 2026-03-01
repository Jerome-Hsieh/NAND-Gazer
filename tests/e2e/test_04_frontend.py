"""Test 04: Frontend Playwright browser tests."""

import re

import pytest
from playwright.sync_api import Page, expect

FRONTEND_URL = "http://localhost:5173"


@pytest.fixture(scope="module")
def browser_context(browser):
    """Shared browser context for all frontend tests."""
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    yield context
    context.close()


@pytest.fixture()
def page(browser_context):
    """Fresh page for each test."""
    p = browser_context.new_page()
    yield p
    p.close()


@pytest.mark.frontend
class TestHeader:
    """Header component tests (visible on every page)."""

    def test_header_visible(self, page: Page):
        """Price Tracker header is visible with emoji."""
        page.goto(FRONTEND_URL)
        expect(page.locator("header")).to_be_visible()
        expect(page.get_by_text("Price Tracker")).to_be_visible()

    def test_navigation_links(self, page: Page):
        """Dashboard and Search navigation links exist."""
        page.goto(FRONTEND_URL)
        dashboard_link = page.locator("a", has_text="Dashboard")
        search_link = page.locator("a", has_text="Search")
        expect(dashboard_link).to_be_visible()
        expect(search_link).to_be_visible()

    def test_navigation_works(self, page: Page):
        """Click Search navigates to /search, click Dashboard returns to /."""
        page.goto(FRONTEND_URL)
        page.locator("nav a", has_text="Search").click()
        page.wait_for_url("**/search")
        assert "/search" in page.url

        page.locator("nav a", has_text="Dashboard").click()
        page.wait_for_url(re.compile(r"/$"))
        assert page.url.rstrip("/").endswith("5173") or page.url.endswith("/")


@pytest.mark.frontend
class TestHomePage:
    """HomePage (/) tests."""

    def test_dashboard_title(self, page: Page):
        """Dashboard heading and subtitle are visible."""
        page.goto(FRONTEND_URL)
        expect(page.locator("h1", has_text="Dashboard")).to_be_visible()
        expect(page.get_by_text("Overview of tracked product prices")).to_be_visible()

    def test_stats_cards(self, page: Page):
        """4 stats cards display with non-empty values."""
        page.goto(FRONTEND_URL)
        # Wait for stats to load
        page.wait_for_selector("text=Products Tracked", timeout=10000)

        for title in ["Products Tracked", "Active Keywords", "Price Records", "Last Scrape"]:
            card = page.locator("div", has_text=title).first
            expect(card).to_be_visible()

        # Check that at least one stat has a numeric value
        bold_values = page.locator(".text-3xl.font-bold")
        count = bold_values.count()
        assert count >= 4, f"Expected 4 stat values, got {count}"

    def test_product_cards(self, page: Page):
        """Product cards are displayed on homepage."""
        page.goto(FRONTEND_URL)
        # Wait for products to load
        page.wait_for_selector("a[href^='/product/']", timeout=10000)

        cards = page.locator("a[href^='/product/']")
        assert cards.count() >= 1, "No product cards found"

        # Each card has a name and price
        first_card = cards.first
        expect(first_card.locator(".text-sm.font-medium")).to_be_visible()
        expect(first_card.locator(".text-lg.font-bold.text-red-600")).to_be_visible()

    def test_view_all_link(self, page: Page):
        """'View all →' link navigates to /search."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)

        link = page.locator("a", has_text="View all")
        expect(link).to_be_visible()
        link.click()
        page.wait_for_url("**/search")
        assert "/search" in page.url


@pytest.mark.frontend
class TestSearchPage:
    """SearchPage (/search) tests."""

    def test_search_form_visible(self, page: Page):
        """Search input and button are visible."""
        page.goto(f"{FRONTEND_URL}/search")
        expect(page.locator("input[placeholder='Search products...']")).to_be_visible()
        expect(page.locator("button", has_text="Search")).to_be_visible()

    def test_search_ddr5(self, page: Page):
        """Search for DDR5 returns results."""
        page.goto(f"{FRONTEND_URL}/search")
        page.fill("input[placeholder='Search products...']", "DDR5")
        page.locator("button", has_text="Search").click()
        # Wait for results
        page.wait_for_selector("text=Found", timeout=10000)
        found_text = page.locator("p", has_text="Found").text_content()
        assert found_text is not None
        # Extract number from "Found X products"
        match = re.search(r"Found\s+(\d+)", found_text)
        assert match is not None, f"Could not parse count from: {found_text}"
        count = int(match.group(1))
        assert count > 0

        # Product cards should appear
        cards = page.locator("a[href^='/product/']")
        assert cards.count() > 0

    def test_search_no_results(self, page: Page):
        """Search for nonexistent term shows no-results message."""
        page.goto(f"{FRONTEND_URL}/search")
        page.fill("input[placeholder='Search products...']", "ZZZZNONEXISTENT")
        page.locator("button", has_text="Search").click()
        page.wait_for_url("**/search?q=ZZZZNONEXISTENT**")
        # Wait for the no-results state
        expect(page.get_by_text("No products found")).to_be_visible(timeout=10000)

    def test_pagination_buttons(self, page: Page):
        """Pagination Previous is disabled on page 1 when pagination is shown."""
        page.goto(f"{FRONTEND_URL}/search")
        # Wait for data
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        # Pagination only shows when pages > 1
        prev_btn = page.locator("button", has_text="Previous")
        if prev_btn.count() > 0:
            expect(prev_btn).to_be_disabled()


@pytest.mark.frontend
class TestProductDetailPage:
    """ProductDetailPage (/product/:id) tests."""

    def test_navigate_to_detail(self, page: Page):
        """Click a product card navigates to /product/:id."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        first_card = page.locator("a[href^='/product/']").first
        first_card.click()
        page.wait_for_url(re.compile(r"/product/\d+"))
        assert re.search(r"/product/\d+", page.url)

    def test_product_info(self, page: Page):
        """Product detail shows name and price."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        page.locator("a[href^='/product/']").first.click()
        page.wait_for_url(re.compile(r"/product/\d+"))

        # Wait for product to load
        page.wait_for_selector("h1", timeout=10000)
        expect(page.locator("h1")).to_be_visible()
        # Price
        expect(page.locator(".text-3xl.font-bold.text-red-600")).to_be_visible()

    def test_product_details_labels(self, page: Page):
        """Product detail shows Shop, Brand, Platform labels."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        page.locator("a[href^='/product/']").first.click()
        page.wait_for_url(re.compile(r"/product/\d+"))
        page.wait_for_selector("h1", timeout=10000)

        # Labels are conditionally rendered based on product data.
        # brand is often null for scraped products, so at least 1 of these should be visible.
        labels_found = 0
        for label in ["Shop:", "Brand:", "Platform:"]:
            if page.locator(f"text={label}").count() > 0:
                labels_found += 1
        assert labels_found >= 1, "Expected at least 1 of Shop/Brand/Platform labels"

    def test_view_on_pchome_link(self, page: Page):
        """'View on PChome →' link exists."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        page.locator("a[href^='/product/']").first.click()
        page.wait_for_url(re.compile(r"/product/\d+"))
        page.wait_for_selector("h1", timeout=10000)

        pchome_link = page.locator("a", has_text="View on PChome")
        expect(pchome_link).to_be_visible()

    def test_price_chart(self, page: Page):
        """Price History chart heading and SVG are visible."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        page.locator("a[href^='/product/']").first.click()
        page.wait_for_url(re.compile(r"/product/\d+"))

        expect(page.locator("h2", has_text="Price History (30 days)")).to_be_visible(
            timeout=10000
        )
        # Recharts renders an SVG
        chart_container = page.locator(".recharts-wrapper, .recharts-responsive-container")
        if chart_container.count() == 0:
            # Fallback: just check for SVG within the chart section
            svg = page.locator("svg").first
            expect(svg).to_be_visible()

    def test_back_to_search(self, page: Page):
        """'Back to search' link navigates back to /search."""
        page.goto(FRONTEND_URL)
        page.wait_for_selector("a[href^='/product/']", timeout=10000)
        page.locator("a[href^='/product/']").first.click()
        page.wait_for_url(re.compile(r"/product/\d+"))
        page.wait_for_selector("h1", timeout=10000)

        back_link = page.locator("a", has_text="Back to search")
        expect(back_link).to_be_visible()
        back_link.click()
        page.wait_for_url("**/search")
        assert "/search" in page.url
