"""
Facebook Scraper Script (facebook_scraper.py)

Purpose:
This script automates the process of browsing to Facebook's mobile website (m.facebook.com),
logging in, searching for a specific keyword ("Bkash" as per requirements),
and then attempting to extract the text content of the three most recent posts
from the search results page.

Dependencies:
- Python 3.x
- Playwright library for browser automation.
  The script attempts to install Playwright and its browser drivers automatically
  if they are not found. However, manual installation might sometimes be necessary:
    pip install playwright
    python -m playwright install

How to Run:
1. Ensure Python 3 is installed.
2. Save this script as `facebook_scraper.py`.
3. (CRITICAL FOR FUNCTIONALITY & SECURITY) Set Environment Variables for Credentials:
   For the script to log in to Facebook, you MUST provide your credentials
   via environment variables. This is a security measure to avoid hardcoding
   sensitive information directly into the script.

   In your terminal (Linux/macOS):
     export FB_EMAIL="your_facebook_email@example.com"
     export FB_PASSWORD="your_facebook_password"

   In PowerShell (Windows):
     $env:FB_EMAIL="your_facebook_email@example.com"
     $env:FB_PASSWORD="your_facebook_password"

   If these environment variables (FB_EMAIL, FB_PASSWORD) are not set, the script
   will fall back to using placeholder values ("YOUR_EMAIL", "YOUR_PASSWORD").
   LOGIN WILL FAIL with these placeholders. You MUST use valid credentials
   via environment variables for the script to work.

4. Run the script from your terminal:
   python facebook_scraper.py

Functionality Overview:
- Initializes Playwright and launches a Chromium browser.
- Navigates to m.facebook.com.
- Attempts to handle cookie consent banners.
- Attempts to log in using the credentials provided via environment variables.
- If login is successful, it searches for the keyword "Bkash".
- If search is successful, it attempts to extract the text from the 3 most recent posts.
- Prints the extracted posts to the console.
- Takes screenshots at various stages for debugging (e.g., homepage_loaded.png, login_success.png, search_results.png). These are saved in the same directory as the script.

Note on Selectors:
Facebook's website structure can change frequently. The CSS selectors used in this
script (for login fields, search bar, posts, etc.) are based on observations at
the time of writing and may become outdated. If the script fails at a certain step
(e.g., cannot find login button, cannot extract posts), it's likely that the
selectors need to be updated by inspecting the current m.facebook.com HTML structure.
"""

# --- Existing Security Warning (kept for emphasis) ---
# !!! SECURITY WARNING !!!
# HARDCODING CREDENTIALS IS A SIGNIFICANT SECURITY RISK.
# It is strongly recommended to use environment variables as described above.
# ---

import sys
import subprocess
import time
import os

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ModuleNotFoundError:
    print("Playwright library not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright'])
        print("Playwright library installed successfully.")
        print("Now installing browser drivers (this might take a moment)...")
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])
        print("Playwright browser drivers installed successfully.")
        print("\nInstallation complete. Please re-run the script.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Playwright installation: {e}")
        print("Please try installing manually: pip install playwright && python -m playwright install")
    sys.exit("Exiting due to initial setup. Please re-run the script.")


def login_to_facebook(page, email, password):
    """
    Attempts to log into Facebook using the provided credentials on the given Playwright page.
    Handles common login page elements and basic error scenarios.
    """
    print("Attempting to log in...")
    try:
        # Wait for email field and fill it
        page.wait_for_selector('input[name="email"]', timeout=10000, state="visible")
        page.fill('input[name="email"]', email)
        print("Email field filled.")

        # Wait for password field and fill it
        page.wait_for_selector('input[name="pass"]', timeout=10000, state="visible")
        page.fill('input[name="pass"]', password)
        print("Password field filled.")

        # Common selectors for the login button on m.facebook.com
        login_button_selectors = [
            'button[name="login"]', 
            'button[type="submit"]',
            'input[type="submit"][value="Log In"]' # More specific input type
        ]
        
        login_button_found = False
        for selector in login_button_selectors:
            button = page.query_selector(selector)
            if button and button.is_visible():
                button.click()
                login_button_found = True
                print(f"Clicked login button using selector: '{selector}'")
                break
        
        if not login_button_found:
            print("Login failed: Could not find a visible login button. Facebook's page structure might have changed.")
            page.screenshot(path="login_button_not_found.png")
            return False

        # Wait for page reaction after login attempt (e.g., navigation, error message)
        page.wait_for_timeout(5000) 

        # Check for common login failure indicators
        if "checkpoint" in page.url.lower():
             print("Login failed: Facebook is asking for a security checkpoint. Manual intervention may be required.")
             page.screenshot(path="login_failed_checkpoint.png")
             return False
        elif page.query_selector('input[name="email"]') and page.query_selector('input[name="email"]').is_visible():
             print("Login failed: Potentially incorrect credentials or unexpected page. The email input field is still visible.")
             page.screenshot(path="login_failed_email_still_visible.png")
             return False
        elif "login" in page.url.lower() and "home.php" not in page.url.lower() and "search" not in page.url.lower() :
            print("Login failed: Still on a login-related page. Double-check credentials or page structure changes.")
            page.screenshot(path="login_failed_still_on_login_page.png")
            return False
        else:
            print("Login appears successful (no immediate failure indicators found).")
            page.screenshot(path="login_success_evidence.png")
            return True

    except PlaywrightTimeoutError:
        print("Login failed: Timeout occurred during login (e.g., crucial elements like email/password fields not found). Facebook's page structure might have changed.")
        page.screenshot(path="login_timeout_error.png")
        return False
    except Exception as e:
        print(f"Login failed: An unexpected error occurred: {e}")
        page.screenshot(path="login_generic_error.png")
        return False

def search_facebook(page, keyword):
    """
    Performs a search on Facebook for the given keyword.
    Assumes the user is already logged in and on a page with a search interface.
    """
    print(f"\nSearching for keyword '{keyword}'...")
    try:
        # Common selectors for search trigger (icon/button) or direct search input field
        search_trigger_selectors = [
            'a[aria-label*="Search"]', 'button[aria-label*="Search"]', # Using *= for partial match
            'a[href*="/search/"]', 'button[data-testid*="search_input"]',
            'input[type="search"]', 'input[name="q"]' # 'q' is a common name for search inputs
        ]
        search_field_actual_selector = 'input[type="search"], input[name="q"]' # Default if trigger is not input
        
        search_interaction_done = False
        for selector in search_trigger_selectors:
            trigger_element = page.query_selector(selector)
            if trigger_element and trigger_element.is_visible():
                print(f"Found search interaction element with selector: '{selector}'")
                if trigger_element.tag_name() == 'input':
                    search_field_actual_selector = selector 
                    print("Search element is an input field. Using it directly.")
                    trigger_element.fill(keyword)
                else: 
                    print("Search element is a button/link. Clicking to reveal input field...")
                    trigger_element.click()
                    page.wait_for_timeout(2000) # Wait for input field to appear/become active
                    # After click, the actual input field might be different
                    page.fill(search_field_actual_selector, keyword)
                
                print(f"Filled search input with '{keyword}'.")
                page.screenshot(path="search_keyword_filled.png")
                
                # Press Enter to submit the search
                page.press(search_field_actual_selector, 'Enter')
                search_interaction_done = True
                break 
        
        if not search_interaction_done:
            print("Search failed: Could not find or interact with a search trigger/input. Page structure may have changed.")
            page.screenshot(path="search_trigger_not_found.png")
            return False
        
        # Wait for search results to load (can be a navigation or dynamic update)
        page.wait_for_timeout(7000) 
        
        print(f"Search for '{keyword}' submitted. Current URL: {page.url}")
        page.screenshot(path="search_results_page.png")
        
        # Basic check if search results page seems valid
        if keyword.lower() not in page.url.lower() and keyword.lower() not in page.title().lower():
            print(f"Warning: Search for '{keyword}' submitted, but URL and page title do not strongly indicate a search results page for this keyword. Manual verification of screenshot advised.")
        return True

    except PlaywrightTimeoutError:
        print(f"Search failed: Timeout occurred during search for '{keyword}'. Elements might not be available or page structure changed.")
        page.screenshot(path="search_timeout_error.png")
        return False
    except Exception as e:
        print(f"Search failed: An unexpected error occurred during search for '{keyword}': {e}")
        page.screenshot(path="search_generic_error.png")
        return False

def extract_recent_posts(page, count):
    """
    Attempts to extract text content from the 'count' most recent posts on the current page.
    This is highly dependent on Facebook's current HTML structure for posts.
    """
    print(f"\nExtracting up to {count} recent posts...")
    extracted_posts = []

    # List of potential selectors for post containers. These are subject to change.
    # The goal is to find a selector that reliably wraps individual posts.
    post_container_selectors = [
        "article",                            # Standard HTML5 tag for articles/posts
        "div[role='article']",                # ARIA role often used for posts
        "div[data-pagelet^='FeedUnit']",      # Facebook-specific attribute
        "div[data-mcomponent='ServerFeedUnit']",# Another Facebook attribute (mbasic)
        "div[aria-posinset]"                  # Generic ARIA attribute for items in a set
    ]
    
    post_elements = []
    selected_selector_info = "None"
    for selector in post_container_selectors:
        print(f"Trying post container selector: '{selector}'...")
        try:
            # Wait for at least one element matching the selector to be visible
            page.wait_for_selector(selector, timeout=7000, state="visible") 
            elements_found = page.query_selector_all(selector)
            
            if elements_found:
                visible_elements = [el for el in elements_found if el.is_visible()]
                if visible_elements:
                    post_elements = visible_elements
                    selected_selector_info = f"'{selector}' (found {len(post_elements)} visible elements)"
                    print(f"Successfully found {len(post_elements)} visible post containers using selector: '{selector}'.")
                    break # Use the first selector that yields visible results
            print(f"Selector '{selector}' did not yield any visible results.")
        except PlaywrightTimeoutError:
            print(f"Selector '{selector}' timed out or no visible elements found with it.")
            continue 
    
    if not post_elements:
        print("Post extraction failed: No suitable post container elements found with any of the attempted selectors. Facebook's page structure may have changed or no posts are visible on the page.")
        page.screenshot(path="no_posts_found_on_page.png")
        return extracted_posts

    print(f"Processing up to {count} posts from elements found with {selected_selector_info}...")
    for i, post_element in enumerate(post_elements):
        if i >= count:
            break
        try:
            post_text = post_element.inner_text()
            if post_text and post_text.strip():
                # Basic filter to avoid very short, non-content texts (e.g., "Like", "Comment")
                # or common interaction notifications if they are mistakenly captured as posts.
                text_lower = post_text.lower()
                common_non_post_phrases = [
                    "commented on this", "shared this", "reacted to this", 
                    "suggested for you", "people you may know", "is live now"
                ]
                # This filter can be refined. The length check helps avoid overly aggressive filtering.
                if len(post_text.strip()) < 75 and any(phrase in text_lower for phrase in common_non_post_phrases):
                    print(f"  Skipping potential post {i+1} (from {selected_selector_info}): Seems like a short notification/interaction. Content preview: '{post_text[:100].strip()}'...")
                    continue
                
                extracted_posts.append(post_text.strip())
                print(f"  Extracted post {i+1} (from {selected_selector_info}): '{post_text[:150].strip()}'...")
            else:
                print(f"  Post {i+1} (from {selected_selector_info}) had no extractable text content or was empty.")
        except Exception as e:
            print(f"  Error extracting text from post {i+1} (from {selected_selector_info}): {e}")

    page.screenshot(path="post_extraction_attempt_done.png")
    
    if not extracted_posts:
        print(f"Found potential post elements with {selected_selector_info}, but could not extract meaningful text from any of them that passed filters.")
    else:
        print(f"Successfully extracted {len(extracted_posts)} posts that met criteria.")

    return extracted_posts


def main():
    """
    Main function to orchestrate the Facebook scraping process.
    """
    print("Script starting...")
    print("For details on usage, dependencies, and credential setup, please see the docstring at the top of this script.")

    # --- Credential Handling ---
    # Fetches Facebook credentials from environment variables FB_EMAIL and FB_PASSWORD.
    # Falls back to placeholders if environment variables are not set, with a strong warning.
    FB_EMAIL_PLACEHOLDER = "YOUR_EMAIL" # This will NOT work for actual login
    FB_PASSWORD_PLACEHOLDER = "YOUR_PASSWORD" # This will NOT work for actual login

    fb_email = os.environ.get('FB_EMAIL')
    fb_password = os.environ.get('FB_PASSWORD')

    using_placeholders = False
    if not fb_email or not fb_password:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! CRITICAL WARNING: FB_EMAIL or FB_PASSWORD environment variables not set. !!!")
        print("!!! Falling back to NON-FUNCTIONAL placeholder credentials in the script.    !!!")
        print("!!! LOGIN WILL FAIL. This is INSECURE and NOT for actual use.              !!!")
        print("!!! Please set FB_EMAIL and FB_PASSWORD environment variables with your    !!!")
        print("!!! actual Facebook credentials for the script to attempt login.           !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        fb_email = FB_EMAIL_PLACEHOLDER
        fb_password = FB_PASSWORD_PLACEHOLDER
        using_placeholders = True
    # --- End Credential Handling ---

    with sync_playwright() as p:
        browser = None # Initialize browser variable
        try:
            print("Launching browser...")
            # browser = p.chromium.launch(headless=False) # Use for debugging to see the browser
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Set a mobile user agent as we are targeting m.facebook.com
            mobile_user_agent = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
            page.set_extra_http_headers({"User-Agent": mobile_user_agent})
            print(f"Browser launched with user agent: {mobile_user_agent}")

            print("Navigating to https://m.facebook.com...")
            page.goto('https://m.facebook.com', timeout=60000)
            print("Successfully navigated to Facebook's mobile homepage.")
            page.screenshot(path="facebook_home_page.png")

            # Attempt to handle cookie consent pop-ups if they appear
            # These selectors are examples and might need adjustment based on current FB UI
            cookie_banner_selectors = [
                "button[data-cookiebanner='accept_button']", "//button[contains(text(), 'Allow all cookies')]",
                "//button[contains(text(), 'Accept All')]", "//button[contains(text(), 'Allow essential and optional cookies')]"
            ]
            cookie_banner_clicked = False
            for selector in cookie_banner_selectors:
                button = page.query_selector(selector)
                if button and button.is_visible():
                    try:
                        print(f"Attempting to click cookie consent button with selector: '{selector}'")
                        button.click(timeout=5000) # Short timeout for click
                        cookie_banner_clicked = True
                        print("Clicked a cookie consent button.")
                        time.sleep(2) # Wait for banner to disappear
                        page.screenshot(path="cookie_consent_clicked.png")
                        break 
                    except Exception as e:
                        print(f"Could not click cookie button with selector '{selector}': {e}")
                        page.screenshot(path="cookie_consent_click_error.png")
            if not cookie_banner_clicked:
                print("No cookie consent banner found or clicked with the provided selectors.")
            
            login_successful = False
            if using_placeholders:
                print("\nWARNING: Using placeholder credentials. Login will be attempted but is expected to fail.")
                print("To test full functionality, please provide actual credentials via environment variables FB_EMAIL and FB_PASSWORD.")
            
            # Proceed with login attempt regardless of placeholder status, to show the process
            # The login_to_facebook function will indicate failure with placeholders
            print("\nProceeding with login attempt...")
            login_successful = login_to_facebook(page, fb_email, fb_password)

            if login_successful:
                print("\nLogin successful. Proceeding to search.")
                search_keyword = "Bkash" # As per requirement
                search_successful = search_facebook(page, search_keyword)
                
                if search_successful:
                    print(f"\nSearch for '{search_keyword}' initiated successfully. Proceeding to extract posts.")
                    # Now, attempt to extract posts from the search results page
                    posts = extract_recent_posts(page, 3) # As per requirement (3 posts)
                    if posts:
                        print(f"\n--- Extracted {len(posts)} Posts for '{search_keyword}' ---")
                        for i, post_content in enumerate(posts):
                            print(f"\nPOST {i+1}:")
                            print(post_content)
                            print("-----------------------------------")
                    else:
                        print(f"\nNo posts were extracted for '{search_keyword}', or extraction yielded no text that passed filters.")
                else:
                    print(f"\nSearch for '{search_keyword}' failed or could not be completed. Skipping post extraction.")
            else:
                print("\nLogin failed or was effectively skipped due to placeholder credentials. Further actions (search, post extraction) cannot be performed.")

        except PlaywrightTimeoutError as pte:
            print(f"A global timeout occurred in the main execution flow: {pte}")
            if 'page' in locals() and page: page.screenshot(path="main_global_timeout_error.png")
        except Exception as e:
            print(f"An unexpected error occurred in the main execution flow: {e}")
            if 'page' in locals() and page: page.screenshot(path="main_global_generic_error.png")
        finally:
            if browser:
                browser.close()
                print("\nBrowser closed.")
            print("\nScript finished.")


if __name__ == "__main__":
    main()
