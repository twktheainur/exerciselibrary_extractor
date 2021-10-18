from pathlib import Path

import requests
import selenium
from bs4 import BeautifulSoup
import json
import logging
import re

from mne.externals.tqdm import tqdm
from selenium.webdriver.common.by import By

logging.basicConfig(format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger("extract_dataset")

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options

options = Options()
# options.add_argument('--headless')
# options.add_argument('--disable-gpu')

driver = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=options)

headers = {
    'User-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36",
    'Origin': "https://www.functionalmovement.com",
    'Referrer': 'https://www.functionalmovement.com/exercises',
}

query_result = requests.post("https://www.functionalmovement.com/exercises/exercises_read", headers=headers)

if query_result.status_code < 300:
    parsed_data = json.loads(query_result.text)
    for exercise in parsed_data['Data']:
        output_metadata = dict()
        output_metadata['id'] = exercise['ExerciseID']
        if not Path(f"corpus/{output_metadata['id']}.json").exists():
            output_metadata['name'] = exercise['Name']
            output_metadata['summary'] = exercise['Summary']
            output_metadata['position'] = exercise['PositionId']
            output_metadata['categories'] = exercise['Categories']
            output_metadata['body_parts'] = exercise['BodyPartIds']
            uri = exercise['UrlName']

            exercise_page_url = f"https://www.functionalmovement.com/Exercises/{output_metadata['id']}/{uri}"
            driver.get(exercise_page_url)
            objective_text = driver.find_element(by=By.XPATH, value="//div[@class='col-md-8']/div[1]/div[1]").text
            output_metadata['objective'] = objective_text
            try:
                position_name = driver.find_element(by=By.XPATH, value="//div[@class='col-md-8']/div[1]/div[2]//a").text
                output_metadata['position_name'] = position_name
            except selenium.common.exceptions.NoSuchElementException:
                logging.warning(f"No action name present for exercise {output_metadata['id']}.")

            video_script = driver.find_element(by=By.XPATH,
                                               value="//div[@class='col-md-8']/div[2]/script[2]").get_attribute(
                "innerHTML")

            extract_vide_json_regex = re.compile(".*\"playlist\": \"([^\"]*)\".*")
            match = extract_vide_json_regex.match(video_script.strip().replace("\n", " "))
            if match is not None:
                cdn_url = match.group(1)
                video_json = requests.get(cdn_url, headers=headers)
                if video_json.status_code < 300:
                    video_json_value = video_json.text
                    parsed_video_json = json.loads(video_json_value)
                    video_data = parsed_video_json['playlist'][0]
                    output_metadata['video_duration'] = video_data['duration']
                    highest_res_source = video_data['sources'][-1]
                    output_metadata['video_resolution'] = highest_res_source['label']
                    output_metadata['video_size'] = highest_res_source['filesize']
                    response = requests.get(highest_res_source['file'], stream=True)
                    video_filename = f"corpus/videos/{output_metadata['id']}.mp4"
                    path = Path(video_filename)
                    if not path.exists():
                        with open(f"corpus/videos/{output_metadata['id']}.mp4", "wb") as handle:
                            for data in tqdm(response.iter_content(), desc=f"Downloading {output_metadata['id']}.mp4",
                                             total=output_metadata['video_size']):
                                handle.write(data)
                    else:
                        logger.info(f"{video_filename} already downloaded, skipping.")

            paragraphs = []
            try:
                paragraphs.extend(driver.find_elements(by=By.XPATH, value="//div[@class='col-md-8']/div"))
            except:
                pass
            try:
                paragraphs.extend(driver.find_elements(by=By.XPATH, value="//div[@class='col-md-8']/p"))
            except:
                pass

            whole_text = ""
            for p in paragraphs:
                text = p.text
                if "Set-up:" in text or "Setup:" in text:
                    output_metadata['set_up_text'] = text.split(":")[1]
                elif "Action:" in text:
                    output_metadata['action_text'] = text.split(":")[1]
                elif "Return:" in text:
                    output_metadata['return_position_text'] = text.split(":")[1]
                else:
                    if "Starting Position:" not in text and "seconds of" not in text:
                        whole_text += text

            if len(whole_text) > 0 and 'action_text' not in output_metadata:
                output_metadata['action_text'] = whole_text
            related_links = driver.find_elements(by=By.CSS_SELECTOR, value="#article-stream .groups a")
            related_exercises = [int(link.get_attribute("href").split("/")[-2]) for link in related_links]
            output_metadata['related_exercises'] = related_exercises
            with open(f"corpus/{output_metadata['id']}.json", 'w') as outfile:
                json.dump(output_metadata, outfile, sort_keys=True, indent=2)
