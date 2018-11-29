import sys
import time
import queue
import json
import threading

import requests
import bs4

class Crawler(threading.Thread):
    def __init__(self,
                 base_url,
                 seed_pages=[""],
                 crawl_count=50,
                 time_delay=0.1,
                 verbose=False,
                 recipe_callback=None,
                 recipe_callback_args=(),
                 recipe_callback_kwargs={}):
        """Sets up the crawler object with some default args"""
        threading.Thread.__init__(self)
        self.base_url = base_url
        self.pages_to_crawl = queue.Queue()
        for page in seed_pages:
            self.pages_to_crawl.put(page)
        self.pages_seen = set(seed_pages)
        self.crawl_count = crawl_count
        self.time_delay = time_delay
        self.recipe_callback = recipe_callback
        self.recipe_callback_args = recipe_callback_args
        self.recipe_callback_kwargs = recipe_callback_kwargs
        self.verbose = verbose
        self.recipes = []
        self.start()

    def run(self):
        """Runs the crawler"""
        count = 0
        while count < self.crawl_count and not self.pages_to_crawl.empty():
            self.v_print("Crawling page {} of {}".format(count, self.crawl_count))
            self.crawl_next()
            count = count + 1
            self.v_print("Sleeping for {} seconds".format(self.time_delay))
            sys.stdout.flush()
            time.sleep(self.time_delay)

    def crawl_next(self):
        """Crawls the next page in the queue"""
        try:
            page_name = self.pages_to_crawl.get()
        except queue.Empty:
            self.v_print("Crawl queue is empty")
            return False
        self.v_print("Full url: {}".format(self.base_url + page_name))

        recipes = get_recipes_from_url(self.base_url + page_name)
        self.v_print("Found {} recipes for a total of {} recipes".format(len(recipes), len(self.recipes)))
        self.recipes += recipes
        if self.recipe_callback is not None:
            # Runs the recipe callback with args for each recipe found
            for recipe in recipes:
                self.recipe_callback(recipe, *(self.recipe_callback_args), **(self.recipe_callback_kwargs))

        links = get_links_from_url(self.base_url + page_name)
        # Filters out links not from the base_url
        allowed_links = [link for link in links if link[:len(self.base_url)] == self.base_url]
        for link in allowed_links:
            # Records pages to crawl later, if not already seen
            page = link[len(self.base_url):]
            if page not in self.pages_seen:
                self.pages_to_crawl.put(page)
                self.pages_seen.add(page)
        return True

    def get_recipes(self):
        """Gets the lift of scraped recipes"""
        return self.recipes

    def v_print(self, string):
        """Prints, if in verbose mode"""
        if self.verbose:
            print(string)

def get_links_from_url(url):
    """Returns a list of links from the url"""
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.text, "html.parser")
    # Gets all "a" tags with "href" attribute
    link_tag_list = soup.find_all("a", href=True)
    return [link_tag["href"] for link_tag in link_tag_list]

def get_recipes_from_url(url):
    """Returns a list of recipe objects following Google's schema"""
    page = requests.get(url)
    soup = bs4.BeautifulSoup(page.text, "html.parser")
    # Gets all "script" tags with type "application/ld+json"
    json_tag_list = soup.find_all(lambda tag: tag.name == "script" and tag.get("type", "") == "application/ld+json")
    # Converts "script" tag text to json object
    json_obj_list = [json.loads(" ".join(json_tag.text.split())) for json_tag in json_tag_list]
    # Filters by objects that have the "Recipe" schema type
    return [json_obj for json_obj in json_obj_list if json_obj.get("@type", "") == "Recipe"]


if __name__ == "__main__":
    url = sys.argv[1]
    res = get_recipes_from_url(url)
    json_string = json.dumps(res[0])
    print(json_string)
