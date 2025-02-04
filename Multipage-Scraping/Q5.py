import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_reviews(url):
    # Set up Selenium Chrome driver options
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run headless if you don't want a visible window
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get(url)
    
    reviews_data = []

    # Wait for the page to load key elements.
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
    except Exception as e:
        print("Timed out waiting for page to load.")
        driver.quit()
        return

    # Extract Restaurant Name and Total Reviews from the first page.
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, 'html.parser')
    
    # Restaurant name extraction (update if needed)
    name_tag = soup.find('h1')
    restaurant_name = name_tag.text.strip() if name_tag and name_tag.text else "Unknown"
    
    # Total reviews count extraction (if available)
    review_count_tag = soup.find(text=re.compile(r'\d+[,\d]* reviews'))
    total_reviews = (re.search(r'([\d,]+)', review_count_tag).group(1)
                     if review_count_tag and re.search(r'([\d,]+)', review_count_tag)
                     else "Unknown")

    page_num = 1
    while True:
        print(f"Scraping page {page_num} ...")
        # Wait for review elements to load on the page.
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//p[contains(@class, "comment__09f24__D0cxf")]'))
            )
        except Exception as e:
            print("No reviews loaded or timeout reached.")
            break

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        
        # Update the review text container as needed.
        review_elements = soup.find_all('p', class_="comment__09f24__D0cxf y-css-1wfz87z")
        
        if not review_elements:
            print("No reviews found on this page.")
        else:
            for review in review_elements:
                # Extract review text
                review_text = review.get_text(separator="\n").strip()
                
                # Extract the rating.
                rating_elem = review.find_previous("div", attrs={"role": "img", "aria-label": True})
                rating = (rating_elem.get("aria-label").split()[0]
                          if rating_elem and rating_elem.get("aria-label")
                          else "Unknown")
                
                # Extract reviewer name:
                # First, attempt to find a container with role="region" that holds the aria-label
                user_region = review.find_previous("div", attrs={"role": "region", "aria-label": True})
                if user_region:
                    reviewer = user_region.get("aria-label").strip()
                else:
                    # Fallback: look for an <a> tag with the expected class.
                    user_elem = review.find_previous("a", class_="y-css-1x1e1r2")
                    reviewer = user_elem.get_text(strip=True) if user_elem else "Unknown"
                
                reviews_data.append([restaurant_name, total_reviews, reviewer, review_text, rating])
        
        # Try to locate the "Next" button to go to the next page.
        try:
            # Yelp pagination links usually have href parameters like "?start=10"
            next_button = driver.find_element(By.XPATH, '//a[contains(@href, "start=") and contains(@class, "next")]')
            driver.execute_script("arguments[0].click();", next_button)
            page_num += 1
            time.sleep(3)  # Wait for the next page to load
        except Exception as e:
            print("No next page found. Ending pagination.")
            break

    driver.quit()

    if reviews_data:
        df = pd.DataFrame(reviews_data, 
                          columns=['Restaurant Name', 'Total Reviews', 'Reviewer', 'Review Text', 'Rating'])
        df.to_csv('reviews.csv', index=False, encoding='utf-8')
        print(f"Data saved to yelp_reviews.csv with {len(reviews_data)} reviews scraped.")
    else:
        print("No review data to save.")

if __name__ == "__main__":
    url = input("Enter the restaurant URL: ").strip()
    scrape_reviews(url)
