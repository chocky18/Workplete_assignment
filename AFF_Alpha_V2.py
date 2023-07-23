# Import necessary modules and libraries
from sys import argv, exit, platform
import openai
import time
from PyPDF2 import PdfFileReader
from playwright.sync_api import sync_playwright
from PyQt5.QtWidgets import QApplication, QPushButton, QMainWindow,QAction, QInputDialog,QFileDialog, QPushButton, QVBoxLayout, QWidget,QTextEdit, QLabel,QLineEdit
from PyQt5.QtGui import QIcon,QPixmap,QFont
from PyQt5.QtCore import QSize,Qt,QPoint,QTimer,QRect
import sys
import json
import re
import playwright
import tiktoken
from lxml import html, etree
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
from langchain.document_loaders import TextLoader
from langchain.document_loaders import PyPDFLoader
from langchain.indexes import VectorstoreIndexCreator
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
import pdfx

# Initialize URL list and index for keeping track of URLs
urlList=[]
urlIndex=0

# Initialize previous command list, a counter, and input data dictionary
previous_command_list = ""
num = 0
input_data={}
fileID=[]

# Initialize a flag to check if an element has been clicked
clicked =False

# Drop-down prompt template
drop_down_prompt_template ="""
You have given drop_down_values which are option IDs with Values (option : <option_id>, Value: <option_value>) and a Sentence or word
Find the most similar value in a list of dictionaries to the given word or sentence
Find the synonym for the given sentence
You have to understand the Values in option and find which value in option is more similar to the Sentence or word

If you guess the which option ID with value is closer to the word, return me the value and name of option data
{"key":value}

format of data options:
[{"option_value": <option_id>,"option_value": <option_id>,...}]
option : <option_id>, Value: <option_value>

Previous_Answer:
A word or sentence

Here are some examples:

EXAMPLE 1:
==================================================
[{"Yes":67,"No":69}]
Previous_Answer:  No, we do not have revenue yet. We are in the process of training a multi-modal system which we think is an opening in the market.
------------------
Previous_Answer: Previous_Answer
data: data
YOUR ANSWER: {'No':69}

EXAMPLE 2:
==================================================

[{"What are you looking for?":31,"Virtual Membership":32,"Full time membership":33,"Hot desk membership":34,"Events":35,"Programmes":36,"Corporate partnership":37}]
Previous_Answer:  We invite you to join us on this exciting journey as we continue to refine and enhance Workplete, ultimately bringing it to the masses.
------------------
Previous_Answer: Previous_Answer
data: data
YOUR ANSWER: {'Full time membership':33}
=================================================
---
MAP THE DATA:
data: $data
Previous_Answer: $Previous_Answer
Your Answer:
"""

# Prompt template
prompt_template = """
Given a simplified HTML representation of a webpage, your task is to identify the appropriate mappings between input IDs and names, as well as text IDs and names within the HTML elements.

Instructions:
1. Map the input ID with the corresponding text name. For example, if an input has the ID "25" and a text element has the value "First Name", map them together.
2. Only map input IDs with text values. Do not include text IDs without corresponding input IDs in the mapping.
3. If there is a button with the name "Start", map it to the corresponding button ID and value. For instance, if a button has the ID "5" and the value "Start", map them together as "Start": 5.
4. If a button named "OK" immediately follows an input ID, map it to the input ID. For example, if a button has the ID "7" and the value "OK", map them together as 7: "OK".
5. Do not map text IDs to other text IDs; only map text names to input IDs.
6. Exclude text names that do not have a corresponding input ID from the mapping.
7. If there are options in a sequence, include them as a list of dictionaries. Each dictionary should have a key-value pair where the key is the option value and the value is the option ID.
   For example, if the question is "How Did You Hear About Dreamit?" and the options are "Dreamit Team Member", "Internet Search", and "Investor or VC", the mapping should be:
   "How Did You Hear About Dreamit?": [{'Dreamit Team Member': 48}, {'Internet Search': 49}, {'Investor or VC': 50}]

Data Format:

input: id="<input_id>" type="text" name="<answer text">
text: id="<text_id" value="<question text">
button: id="<button_id" value="<button text">
checkbox: id="<checkbox_id" value="<checkbox text">
option: id="<option_id" value="<option text">

Here are some examples:


EXAMPLE 1:
==================================================
data:
text: id="0" value="First name"
input: id="1" type="text" name="firstname"
text: id="2" value="Last name"
input: id="3" type="text" name="lastname"
text: id="4" value="Company name"
input: id="5" type="text" name="company"
text: id="6" value="City"
input: id="7" type="text" name="city"
text: id="48" value="Sector*"
select: id="49" name="EditableTextField_55b96"
option: id="50" value="Please select a sector"
option: id="51" value="Aerospace and Defence"
option: id="52" value="Automotive"
option: id="53" value="Charities"
option: id="54" value="Construction"
option: id="55" value="Creative"
option: id="56" value="Digital"
option: id="57" value="Education"
option: id="58" value="Electronics"
option: id="59" value="Energy"
option: id="60" value="Engineering"


------------------
YOUR ANSWER: {"First name":1, "Last name":3, "Company name":5,"City":7,"Sector":[{'Please select a sector':50,'Aerospace and Defence':51,'Automotive':52,'Charities':53,'Construction':54,'Creative':55,'Digital':56,'Education':57,'Electronics':58,'Engineering':59,'Energy':60}]}


==================================================

EXAMPLE 2:
==================================================
data:
text: id="79" value="Accelerator*"
select: id="80" name="EditableTextField_94bc9"
option: id="81" value="Please select a programme"
option: id="82" value="Academic Accelerator"
option: id="83" value="Big Ideas Programme - Perth"
option: id="84" value="Bitesize Business Series"
option: id="85" value="Build, Run and Scale - Perth & Ki

------------------
YOUR ANSWER: {"Accelerator":[{'Please select a programme':81,'Academic Accelerator':82,'Big Ideas Programme - Perth':83,'Bitesize Business Series':84,'Build, Run and Scale - Perth & Ki':85}]}
==================================================

EXAMPLE 3:
==================================================
data:
text: id="41" placeholder="Enter your How Did You Hear About Dreamit?"
text: id="42" value="How Did You Hear About Dreamit?"
select: id="43" name="how_did_you_hear_about_dreamit_"
option: id="44" value="Please Select"
option: id="45" value="Accelerator Rankings"
option: id="46" value="Angel List"
option: id="47" value="Conference or Event"
option: id="48" value="Dreamit Alumni"
option: id="49" value="Dreamit Team Member"
option: id="50" value="Internet Search"
option: id="51" value="Investor or VC"
option: id="52" value="Media Story"
option: id="53" value="Social Media"
option: id="54" value="Video / Youtube"
text: id="55" placeholder="Enter your Select Your Vertical"
text: id="56" value="Select Your Vertical"
text: id="57" value="*"
text: id="58" value="HealthtechSecuretech"
text: id="59" value="Healthtech"
radio: id="60" value="Dreamit HealthTech" type="radio" name="which_dreamit_program_are_you_applying_to_"       
text: id="61" value="Healthtech"
text: id="62" value="Securetech"
radio: id="63" value="Dreamit SecureTech" type="radio" name="which_dreamit_program_are_you_applying_to_"       
text: id="64" value="Securetech"
button: id="65" value="Submit" type="submit"
------------------
YOUR ANSWER: {"How Did You Hear About Dreamit?":[{'Please Select':44,'Accelerator Rankings':45,'Angel List':46,'Conference or Event':47,'Dreamit Alumni':48,'Dreamit Team Member':49,'Internet Search':50,'Investor or VC':51,'Media Story':52,'Social Media':53,'Video / Youtube':54}],"Select Your Vertical":[{'Dreamit HealthTech':60,'Dreamit SecureTech':63}]}


data:$data
YOUR ANSWER:
"""

# Text summarization prompt template
Text_summarization_prompt_template ="""

Summarize the given text into a concise answer.

Text: <input_text>

Your Answer:

EXAMPLE 1:
==================================================
Text Summarize it:
Text: "We are open to investments and are actively seeking additional investments beyond the $250k SAFE from Nat & Daniel to help us achieve our product vision."
YOUR ANSWER: We Looking for Investments

EXAMPLE 2:
==================================================
Text Summarize it:
Text: "I don't have any information."
YOUR ANSWER: I don't Know


EXAMPLE 3:
==================================================
Text Summarize it:
Text: "My email address is chockynaresh18@gmail.com"
YOUR ANSWER: chockynaresh18@gmail.com
=================================================
---
Text Summarize it:
Text: <input_text>
Your Answer:
"""

# Define the Crawler class to interact with web pages using Playwright.
class Crawler:
    def __init__(self):
        # Start the Playwright browser with Chromium and disable headless mode (visible browser window).
        self.browser = (
            sync_playwright()
            .start()
            .chromium.launch(
                headless=False,
            )
        )

        # Create a new page for interacting with web content.
        self.page = self.browser.new_page()

    def get_element_attributes(self, element_info):
    # Function to extract relevant attributes from element information.
    # This function processes the information obtained from the web page,
    # filters out relevant attributes based on the element type, and returns
    # a dictionary containing the relevant attributes along with the element's XPath.

        tag = element_info.get("tag")  # Get the tag name of the element.
        attrs = element_info.get("attributes", {})  # Get all attributes of the element.
        value = element_info.get("value", "")  # Get the value attribute of the element.
        innerText = element_info.get("innerText", "")  # Get the inner text of the element.
        xpath = element_info.get("xpath", "")  # Get the XPath of the element.

        attr_dict = {}  # Initialize a dictionary to store relevant attributes.

        # Determine relevant attributes based on the element's tag and attributes.
        attr_dict = {attr: attrs[attr] for attr in ['value', 'type', 'title', 'placeholder', 'name', 'aria-label', 'role'] if attr in attrs and attrs[attr]}

        # Handle special cases for elements like buttons, text areas, and options.
        if tag in ['button', 'textarea', 'option'] or attrs.get('role') in ['button', 'checkbox', 'radio'] or attr_dict.get('type') in ['submit', 'checkbox', 'radio']:
            # If the element is a button, text area, or option, or if it has specific roles or types,
            # use 'value' or 'innerText' as the relevant attribute if available.
            if value is None or value == "":
                value = innerText
            if value is not None and value != "":
                attr_dict['value'] = value
        elif (tag == 'input' and attrs.get('type') != 'submit') or attr_dict.get('role') == 'textbox':
            # For input elements other than 'submit' and elements with the role 'textbox',
            # use the 'value' attribute as the relevant attribute if available.
            value = attrs.get('value')
            if value is not None and value != "":
                attr_dict['value'] = value
        else:
            # For other elements, if the 'value' attribute is not empty or None,
            # use it as the relevant attribute.
            if value is not None and value.strip():
                attr_dict['value'] = value

        # Return the element's XPath and the relevant attributes as a dictionary.
        return xpath, attr_dict

    def crawl(self):
        script = '''
            (function() {
                function getXPath(element) {
                    if (element === null) {
                        return '';
                    }
                    if (element === document.documentElement) {
                        return '/html';
                    } else if (element === document.body) {
                        return '/html' + '/body';
                    } else {
                        let ix = 0;
                        let siblings = element.parentNode.childNodes;
                        for (let i = 0; i < siblings.length; i++) {
                            let sibling = siblings[i];
                            if (sibling === element) {
                                return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                            }
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                                ix++;
                            }
                        }
                    }
                }

                function getElementInfo(element) {
                    let rect = element.getBoundingClientRect();
                    if (rect.top >= 0 && rect.left >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && rect.right <= (window.innerWidth || document.documentElement.clientWidth)) {
                        let attributes = {};
                        for (let attr of element.attributes) {
                            attributes[attr.name] = attr.value;
                        }

                        let xpath = getXPath(element);
                    let parentElement = element.parentNode;
                        let parentRect = parentElement.getBoundingClientRect();

                        let isVisible = rect.top >= 0 && rect.left >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                        let isParentVisible = parentRect.top >= 0 && parentRect.left >= 0 && parentRect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && parentRect.right <= (window.innerWidth || document.documentElement.clientWidth);

                        return {
                            tag: element.tagName.toLowerCase(),
                            attributes: attributes,
                            value: getDirectTextContent(element),
                            innerText: element.textContent.trim(),
                            xpath: xpath,
                            isVisible: isVisible && isParentVisible
                        };
                    }
                    return null;
                }

                function getDirectTextContent(element) {
                    let text = '';
                    for (let node of element.childNodes) {
                        if (node.nodeType === 3) {
                            text += node.textContent;
                        }
                    }
                    return text.trim();
                }

                function isElementJavaScript(el) {
                    return el.tagName.toLowerCase() === 'script' || el.textContent.includes('function(');
                }

                Array.from(document.querySelectorAll('a[target="_blank"]')).forEach(
                    link => link.removeAttribute('target')
                );

                let elements = document.querySelectorAll('body *');
                let result = [];

                for (let element of elements) {
                    let computedStyle = window.getComputedStyle(element);
                    if ((element.offsetWidth > 0 || element.tagName.toLowerCase() === 'option') && computedStyle.display !== 'none' && !isElementJavaScript(element)) {
                        let info = getElementInfo(element);
                        if (info) {
                            result.push(info);
                        }
                    }
                }

                return result;
            })();
        '''

        
        def extract_elements(script, target_page, iframe_id=None):
        # Function to extract elements from the web page based on the given script.
        # It processes the elements, extracts their attributes, and constructs strings
        # representing their types and relevant attributes.

            elements_in_viewport = target_page.evaluate(script)  # Evaluate the script on the target page to get elements in the viewport.

            for element_info in elements_in_viewport:
                # Extract element attributes and check if it is visible and not hidden by CSS.
                xpath, attr_dict = self.get_element_attributes(element_info)
                display = element_info.get("computedStyle", {}).get("display")
                isVisible = element_info.get("isVisible", True)

                if attr_dict and display != "none" and isVisible:
                    # Assign a unique ID to the element for identification.
                    attr_dict["id"] = id_counter[0]
                    tag = element_info.get("tag")

                    # Construct a string representation for output, based on the element's type and attributes.
                    attr_str = ' '.join([f'id="{attr_dict["id"]}"'] + [f'{key}="{value}"' for key, value in attr_dict.items() if key not in ['id', 'role']])
                    if tag in ['button'] or attr_dict.get('role') in ['button'] or attr_dict.get('type') in ['submit']:
                        output_list.append(f"button: {attr_str}")
                    elif tag in ['select']:
                        output_list.append(f"select: {attr_str}")
                    elif tag in ['option']:
                        output_list.append(f"option: {attr_str}")
                    elif tag == 'input' and attr_dict.get('type') == 'radio':
                        output_list.append(f"radio: {attr_str}")
                    elif tag == 'input' and attr_dict.get('type') == 'checkbox':
                        output_list.append(f"checkbox: {attr_str}")
                    elif tag == 'input' and attr_dict.get('type') != 'submit' or tag == 'textarea' or attr_dict.get('role') == 'textbox':
                        output_list.append(f"input: {attr_str}")
                    # elif tag == 'a' or attr_dict.get('role') in ['link']:
                        # output_list.append(f"link: {attr_str}")
                    else:
                        output_list.append(f"text: {attr_str}")

                    if iframe_id is not None:
                        xpath = f"{iframe_id}{xpath}"
                    xpath_dict[xpath] = attr_dict

                    id_counter[0] += 1

                    # If the element is an iframe, handle its content recursively.
                    if tag == 'iframe':
                        iframe_element = target_page.query_selector(f'xpath={xpath}')
                        if iframe_element:
                            iframe_content = iframe_element.content_frame()
                            iframes_list.append((attr_dict["id"], iframe_content))  # Store the iframe and its ID in the list
                            extract_elements(script, iframe_content, attr_dict["id"])

    
        id_counter = [0]
        xpath_dict = {}
        output_list = []
        iframes_list = []

        # Extract elements in the main page
        extract_elements(script, self.page)

        # print(f"\ntotal no. of elements: {id_counter[0]}")
        return output_list, xpath_dict,iframes_list
    

    def get_xpath_by_id(self, id, xpath_dict):
    # Find the XPath of an element based on its ID from the `xpath_dict`.
    # `xpath_dict` is a dictionary that maps XPaths to element attributes.
        for xpath, attrs in xpath_dict.items():
            if attrs.get('id') == id:
                return xpath
        return None

    def get_iframe_by_xpath(self, xpath, iframes_list):
        # Retrieve the iframe content by its XPath from the `iframes_list`.
        # `iframes_list` is a list of tuples containing iframe ID and its content.
        iframe_id = xpath.split("/")[0]  # Extract the iframe_id from the XPath.
        if iframe_id:
            for id, frame in iframes_list:
                if id == int(iframe_id):
                    return frame
        return None

    def click_element(self, id, xpath_dict, iframes_list):
        # Click on an element identified by its ID.
        xpath = self.get_xpath_by_id(id, xpath_dict)
        frame = self.get_iframe_by_xpath(xpath, iframes_list)
        # If the element is within an iframe, click on it within the iframe context.
        # Otherwise, click on the element directly on the current page.
        if frame:
            xpath = re.sub(r'^\d+/', '/', xpath)  # Remove the iframe_id from the xpath.
            if xpath.split('/')[-1].startswith('option'):
                # If the element is an option, find its parent select element and select the option.
                select_xpath = '/'.join(xpath.split('/')[:-1])
                select_element = frame.query_selector(f'xpath={select_xpath}')
                option_element = frame.query_selector(f'xpath={xpath}')
                value = option_element.get_attribute('value')
                select_element.select_option(value)
            else:
                frame.click(f'xpath={xpath}')
        else:
            if xpath.split('/')[-1].startswith('option'):
                # If the element is an option, find its parent select element and select the option.
                select_xpath = '/'.join(xpath.split('/')[:-1])
                select_element = self.page.query_selector(f'xpath={select_xpath}')
                option_element = self.page.query_selector(f'xpath={xpath}')
                value = option_element.get_attribute('value')
                select_element.select_option(value)
            else:
                self.page.click(f'xpath={xpath}')

    def type_into_element(self, id, xpath_dict, iframes_list, text):
        # Type text into an input element identified by its ID.
        xpath = self.get_xpath_by_id(id, xpath_dict)
        frame = self.get_iframe_by_xpath(xpath, iframes_list)
        # If the input element is within an iframe, type text within the iframe context.
        # Otherwise, type text directly into the input element on the current page.
        if frame:
            xpath = re.sub(r'^\d+/', '/', xpath)  # Remove the iframe_id from the xpath.
            frame.fill(f'xpath={xpath}', text)
        else:
            self.page.fill(f'xpath={xpath}', text)

    def type_and_submit(self, xpath_dict, iframes_list, id, text):
        # Type text into an input element identified by its ID and submit the form.
        xpath = self.get_xpath_by_id(id, xpath_dict)
        frame = self.get_iframe_by_xpath(xpath, iframes_list)
        # If the input element is within an iframe, type text and submit within the iframe context.
        # Otherwise, type text into the input element on the current page and press "Enter" to submit.
        if frame:
            xpath = re.sub(r'^\d+/', '/', xpath)  # Remove the iframe_id from the xpath.
            frame.fill(f'xpath={xpath}', text)
            frame.press(f'xpath={xpath}', 'Enter')
        else:
            self.page.fill(f'xpath={xpath}', text)
            self.page.press(f'xpath={xpath}', 'Enter')

    def scroll_up(self):
        # Scroll up the page by one viewport height.
        current_scroll_position = self.page.evaluate('window.pageYOffset')
        viewport_height = self.page.viewport_size['height']
        new_scroll_position = max(current_scroll_position - viewport_height, 0)
        self.page.evaluate(f'window.scrollTo(0, {new_scroll_position})')


    def scroll_down(self):
        # Scroll down the page by one viewport height.
        current_scroll_position = self.page.evaluate('window.pageYOffset')
        viewport_height = self.page.viewport_size['height']
        new_scroll_position = current_scroll_position + viewport_height
        self.page.evaluate(f'window.scrollTo(0, {new_scroll_position})')


    def goToURL(self,url):
        # Navigate to a given URL.
        try:
            response = self.page.goto(url=url, timeout=0)
            self.page.wait_for_load_state()
            status = response.status if response else "unknown"
            print(f"Navigating to {url} returned status code {status}")
        except playwright._impl._api_types.TimeoutError:
            print("Navigation to the URL took too long!")


    def goPageBack(self):
        # Go back to the previous page in the browser history.
        try:
            response = self.page.go_back(timeout=60000)
            self.page.wait_for_load_state()
            if response:
                print(
                    f"Navigated back to the previous page with URL '{response.url}'."
                    f" Status code {response.status}"
                )
            else:
                print("Unable to navigate back; no previous page in the history")
        except playwright._impl._api_types.TimeoutError:
            print("Navigation took too long!")


if __name__ == "__main__":
    # The main script starts here and runs in an infinite loop until manually terminated.

    while True:
        # Create a new instance of the Crawler class.
        _crawler = Crawler()
        # Set OpenAI API key using the environment variable.
        openai.api_key ="your open ai key"

        import os
        os.environ["OPENAI_API_KEY"] = "your openai key"
        import re

        # The following functions help in providing user instructions, getting the number of tokens in a text string,
        # getting GPT-4 commands for drop-down options, and performing text summarization using GPT-4.

        def print_help():
            # Print available commands and options.
            print(
                "(g) to visit url\n(u) scroll up\n(d) scroll down\n(c) to click\n(t) to type\n" +
                "(h) to view commands again\n(r/enter) to run suggested command\n(o) change objective"
            )


        def num_tokens_from_string(string: str, encoding_name: str) -> int:
            # Returns the number of tokens in a text string.
            encoding = tiktoken.encoding_for_model(encoding_name)
            num_tokens = len(encoding.encode(string))
            return num_tokens

        def get_gpt_command(string_data):
            # Generates GPT-4 command based on the given string data.
            prompt = prompt_template
            prompt = prompt.replace("$data", string_data)
            response = openai.ChatCompletion.create(
                model="gpt-4", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "YOUR ANSWER: "}]
            )
            input_string = response["choices"][0]["message"]["content"]
            return input_string

        def gpt_for_drop_down(optiondata, Previous_Answer):
            # Generates GPT-4 command for drop-down options based on the given option data and previous answer.
            prompt = drop_down_prompt_template
            prompt = prompt.replace("$Previous_Answer", Previous_Answer)
            prompt = prompt.replace("$data", str(optiondata))
            print("options_in_gpt_command", optiondata)
            print("Previous answer", Previous_Answer)
            response = openai.ChatCompletion.create(
                model="gpt-4", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "YOUR ANSWER: "}]
            )
            input_string = response["choices"][0]["message"]["content"]
            return input_string

        def gpt_for_text_summarization(Text):
            # Performs text summarization using GPT-4 based on the given text.
            prompt = Text_summarization_prompt_template
            prompt = prompt.replace("<input_text>", Text)
            response = openai.ChatCompletion.create(
                model="gpt-4", messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "YOUR ANSWER: "}]
            )
            input_string = response["choices"][0]["message"]["content"]
            return input_string
        
        class CustomMainWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Workplete")

                # Set window flags to create a frameless window and keep it on top of other windows.
                self.setWindowFlag(Qt.WindowStaysOnTopHint)
                self.setWindowFlag(Qt.FramelessWindowHint)

                # Set the fixed size of the window
                self.setFixedSize(400, 200)

                # Variables for handling drag and resize behavior.
                self.draggable = False
                self.dragging = False
                self.drag_start_position = None
                self.offset = QPoint()
                self.resize_handle_size=20 # Size of the resize handles.

            def mousePressEvent(self, event):
                # Override the mouse press event to handle dragging of the window.
                if event.button() == Qt.LeftButton:
                    self.dragging = True
                    self.drag_start_position = event.globalPos()

            def mouseMoveEvent(self, event):
                # Override the mouse move event to handle dragging and resizing of the window.
                if self.dragging:
                    delta = event.globalPos() - self.drag_start_position

                    # Check if the mouse is over any of the resize handles.
                    if (
                        event.pos().x() < self.resize_handle_size
                        and event.pos().y() < self.resize_handle_size
                    ):
                        self.resize(self.width() - delta.x(),
                                    self.height() - delta.y())
                        self.move(self.x() + delta.x(), self.y() + delta.y())
                    elif (
                        event.pos().x() > self.width() - self.resize_handle_size
                        and event.pos().y() < self.resize_handle_size
                    ):
                        self.resize(self.width() + delta.x(),
                                    self.height() - delta.y())
                        self.move(self.x(), self.y() + delta.y())
                    elif (
                        event.pos().x() < self.resize_handle_size
                        and event.pos().y() > self.height() - self.resize_handle_size
                    ):
                        self.resize(self.width() - delta.x(),
                                    self.height() + delta.y())
                        self.move(self.x() + delta.x(), self.y())
                    elif (
                        event.pos().x() > self.width() - self.resize_handle_size
                        and event.pos().y() > self.height() - self.resize_handle_size
                    ):
                        self.resize(self.width() + delta.x(),
                                    self.height() + delta.y())
                    else:
                        # If not resizing, move the window.
                        self.move(self.x() + delta.x(), self.y() + delta.y())

                    self.drag_start_position = event.globalPos()

            def mouseReleaseEvent(self, event):
                # Override the mouse release event to stop dragging.
                if event.button() == Qt.LeftButton:
                    self.dragging = False

            # Function to get the resize handle at the specified position 'pos'.
            # The function checks the position relative to the window boundaries and returns the corresponding resize handle.
            def getResizeHandleAt(self, pos):
                handle_size = self.resize_handle_size
                rect = self.rect()  # Get the dimensions of the custom main window.

                # Check if the position 'pos' falls within the area of each resize handle and return the corresponding handle name.
                if QRect(0, 0, handle_size, handle_size).contains(pos):
                    return "TopLeft"
                elif QRect(rect.width() - handle_size, 0, handle_size, handle_size).contains(pos):
                    return "TopRight"
                elif QRect(0, rect.height() - handle_size, handle_size, handle_size).contains(pos):
                    return "BottomLeft"
                elif QRect(rect.width() - handle_size, rect.height() - handle_size, handle_size, handle_size).contains(pos):
                    return "BottomRight"
                elif QRect(0, handle_size, handle_size, rect.height() - 2 * handle_size).contains(pos):
                    return "Left"
                elif QRect(rect.width() - handle_size, handle_size, handle_size, rect.height() - 2 * handle_size).contains(pos):
                    return "Right"
                elif QRect(handle_size, 0, rect.width() - 2 * handle_size, handle_size).contains(pos):
                    return "Top"
                elif QRect(handle_size, rect.height() - handle_size, rect.width() - 2 * handle_size, handle_size).contains(pos):
                    return "Bottom"

                return None  # If the position 'pos' does not fall within any resize handle area, return None.

            # Function to get the cursor type based on the resize handle name.
            def getResizeCursor(self, handle):
                if handle in ["TopLeft", "BottomRight"]:
                    return Qt.SizeFDiagCursor  # Diagonal resize cursor for TopLeft and BottomRight handles.
                elif handle in ["TopRight", "BottomLeft"]:
                    return Qt.SizeBDiagCursor  # Diagonal resize cursor for TopRight and BottomLeft handles.
                elif handle in ["Left", "Right"]:
                    return Qt.SizeHorCursor  # Horizontal resize cursor for Left and Right handles.
                elif handle in ["Top", "Bottom"]:
                    return Qt.SizeVerCursor  # Vertical resize cursor for Top and Bottom handles.

                return Qt.ArrowCursor  # Default cursor for other cases (not resizing).

            # Methods for resizing the window in different directions:

            def resizeTop(self, pos):
                handle_size = self.resize_handle_size
                diff = self.mapToGlobal(QPoint(pos.x(), pos.y())) - \
                    self.mapToGlobal(QPoint(0, 0))
                new_height = self.height() - diff.y()
                if new_height >= self.minimumHeight():
                    self.setGeometry(self.x(), self.y() + diff.y(),
                                    self.width(), new_height)

            def resizeBottom(self, pos):
                handle_size = self.resize_handle_size
                diff = self.mapToGlobal(QPoint(pos.x(), pos.y())) - \
                    self.mapToGlobal(QPoint(0, 0))
                new_height = self.height() + diff.y()
                if new_height >= self.minimumHeight():
                    self.resize(self.width(), new_height)

            def resizeLeft(self, pos):
                handle_size = self.resize_handle_size
                diff = self.mapToGlobal(QPoint(pos.x(), pos.y())) - \
                    self.mapToGlobal(QPoint(0, 0))
                new_width = self.width() - diff.x()
                if new_width >= self.minimumWidth():
                    self.setGeometry(self.x() + diff.x(), self.y(),
                                    new_width, self.height())

            def resizeRight(self, pos):
                handle_size = self.resize_handle_size
                diff = self.mapToGlobal(QPoint(pos.x(), pos.y())) - \
                    self.mapToGlobal(QPoint(0, 0))
                new_width = self.width() + diff.x()
                if new_width >= self.minimumWidth():
                    self.resize(new_width, self.height())

            def is_resizable_area(self, pos):
                # Check if the mouse position is over any of the resize handles.
                width = self.width()
                height = self.height()
                return (
                    pos.x() <= self.resize_handle_size
                    or pos.x() >= width - self.resize_handle_size
                    or pos.y() <= self.resize_handle_size
                    or pos.y() >= height - self.resize_handle_size
                )

            def get_resize_direction(self, pos):
                # Get the direction of resizing based on the mouse position.
                width = self.width()
                height = self.height()
                if pos.x() <= self.resize_handle_size and pos.y() <= self.resize_handle_size:
                    return "topleft"
                elif pos.x() >= width - self.resize_handle_size and pos.y() <= self.resize_handle_size:
                    return "topright"
                elif pos.x() <= self.resize_handle_size and pos.y() >= height - self.resize_handle_size:
                    return "bottomleft"
                elif pos.x() >= width - self.resize_handle_size and pos.y() >= height - self.resize_handle_size:
                    return "bottomright"
                elif pos.x() <= self.resize_handle_size:
                    return "left"
                elif pos.x() >= width - self.resize_handle_size:
                    return "right"
                elif pos.y() <= self.resize_handle_size:
                    return "top"
                elif pos.y() >= height - self.resize_handle_size:
                    return "bottom"
                else:
                    return None

        # Function to create the main application window and handle user interactions
        def create_window():
            # Function to load a PDF, DOC, or CSV file and process it for text retrieval
            def load_file():
                file_dialog = QFileDialog()
                file_path, _ = file_dialog.getOpenFileName(window, 'Select File', '', 'PDF Files (*.pdf);;DOC Files (*.doc *.docx);;CSV Files (*.csv)')

                if file_path:
                    try:
                        loader = PyPDFLoader(file_path)
                        pdf_file = loader.load()
                        
                        # Split the documents into chunks
                        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                        texts = text_splitter.split_documents(pdf_file)
                        
                        # Select which embeddings to use
                        embeddings = OpenAIEmbeddings()
                        
                        # Create the VectorStore to use as the index
                        db = Chroma.from_documents(texts, embeddings)
                        
                        # Expose this index in a retriever interface
                        retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 2})
                        
                        # Create a chain to answer questions
                        qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=retriever, return_source_documents=True)
                        
                        return qa
                    except Exception as e:
                        print(f"Error: Failed to load the file - {e}")
                        return None
                else:
                    # Handle the case when the user cancels file selection
                    return None
            
            # Function to extract information from a PDF file
            def pdf_extract():
                file_dialog = QFileDialog()
                file_path, _ = file_dialog.getOpenFileName(window, 'Select File', '', 'PDF Files (*.pdf);;DOC Files (*.doc *.docx);;CSV Files (*.csv)')
                loader = PyPDFLoader(file_path)
                pdf_file = loader.load()
                print(pdf_file)
                pdf=pdfx.PDFx(file_path)
                print(pdf.get_references_as_dict())
                urlList=pdf.get_references_as_dict()['url']
                url_input.clear()
                url_input.setText(urlList[urlIndex])
                on_submit_clicked()
            
            # Function to handle interactions when a PDF-related action is required
            def pdfCall():
                urlIndex+=1
                url_input.clear() 
                url_input.setText(urlList[urlIndex])
                on_submit_clicked()
                    

            # Function to handle interactions when the user clicks the "Submit" button           
            def on_submit_clicked():
                url = url_input.text()  # Get the URL from the input box
                if url:
                    _crawler.goToURL(url)
                file_path = load_file()
                if file_path:
                    # Execute functions that require the URL and file
                    gpt_cmd = ""
                    while True:
                        start = time.time()
                        visibledom, xpath_dict,iframes_list = _crawler.crawl()
                        print("iframes_list",iframes_list)
                        xpath_dict = {k: v for k, v in xpath_dict.items() if v is not None}                        
                        string_text = "\n".join(visibledom)
                        print("string_text", string_text)
                        gpt_cmd = get_gpt_command(string_text)
                        print("gpt command: ", gpt_cmd)
                        gpt_cmd = gpt_cmd.strip()
                        clicked = False
                        data = {}
                        if len(gpt_cmd) > 0:
                            try:
                                data = eval(gpt_cmd)
                            except Exception as e:
                                print(f"Error in evaluating gpt_cmd: {e}")
                                _crawler.scroll_down()
                            if 'Powered by Typeform' in data:
                                del data['Powered by Typeform']
                            swapped_data = {}

                            for key, value in data.items():
                                if isinstance(key, int):
                                    swapped_data[str(value)] = key
                                else:
                                    swapped_data[key] = value
                            previous_llmaanswer = ''
                            for key, value in data.items():
                                print("key",key)
                                result = file_path({"query": key})
                                llmaanswer = result['result']
                                Text_summarized=gpt_for_text_summarization(llmaanswer)
                                print("llmaanswer",llmaanswer)
                                print("Text_summarized",Text_summarized)
                                clicked=False
                                sub_mappings = {}
                                if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                                    optiondata_str = json.dumps(value)
                                    similarity_check = gpt_for_drop_down(optiondata_str,Text_summarized)
                                    print("similarity_check",similarity_check)
                                    if similarity_check is not None and 'None' not in similarity_check:
                                        data = eval(similarity_check)
                                        for key,value in data.items():
                                            _crawler.click_element(value,xpath_dict, iframes_list)
                                            if key.lower() in['Submit','submit','subscribe']:
                                                clicked=True
                                                pdfCall()
                                    else: 
                                        user_input, ok_pressed = QInputDialog.getText(window, "Popup Window", f"Enter input for {key} with optionIDs {value}: ")              
                                        if ok_pressed:
                                            print("User input:", user_input)
                                            llmaanswer = user_input 
                                            print(type(llmaanswer))
                                            _crawler.click_element(llmaanswer,xpath_dict,iframes_list)      
                                else:
                                    try: 
                                        keywords = ["don't know", "don't","unsure"]
                                        if any(keyword in Text_summarized for keyword in keywords):
                                        # if(["don't know","don't"] in Text_summarized):   
                                            user_input, ok_pressed = QInputDialog.getText(window, "Popup Window", f"Enter input for {key}: ")              
                                            if ok_pressed:
                                                print("User input:", user_input)
                                                Text_summarized=user_input  
                                        _crawler.type_into_element(value,xpath_dict, iframes_list,Text_summarized)
                                    except:
                                        _crawler.click_element(value,xpath_dict,iframes_list)
                                        if key.lower() in['Submit','submit','subscribe']:
                                            clicked=True
                                            pdfCall()
                
                            _crawler.scroll_down()
                            time.sleep(5)

            # Create the main application                            
            app = QApplication(sys.argv)

            # Create the main window
            window = CustomMainWindow()
            window.setStyleSheet("QMainWindow{background-color: black; font-weight: bold; border-radius: 10px;}")

            # window = QMainWindow()
            window.setWindowTitle("Workplete")
            window.setWindowFlag(Qt.WindowStaysOnTopHint)
            window.setWindowFlag(Qt.FramelessWindowHint)
            window.setFixedSize(400, 200)
            window.move(10, 550)

            # Create custom title bar
            title_bar = QWidget(window)
            title_bar.setGeometry(0, 0, 400, 40)
            title_bar.setStyleSheet("background-color: black; ")

            # Create logo
            logo_label = QLabel(window)
            logo_pixmap = QPixmap("logo_new.png").scaledToHeight(40)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setGeometry(8, -2, logo_pixmap.width(), logo_pixmap.height())

            # Create title label
            title_label = QLabel("Workplete", title_bar)
            title_label.setGeometry(70, -5, 200, 50)
            title_label.setStyleSheet("color: #ea9d59; font-size:20px; font-family:'Roboto-Mono';")

            # Create close button
            close_btn = QPushButton(title_bar)
            close_btn.setGeometry(350, -5, 50, 50)
            close_btn.setIcon(QIcon("close.png"))
            close_btn.setIconSize(QSize(20, 20))
            close_btn.setStyleSheet("QPushButton{background-color:#353b48; border:none;}")

            # Connect close button to close application
            close_btn.clicked.connect(window.close)

            or_label=QLabel("---OR---",window)
            or_label.setAlignment(Qt.AlignCenter)
            or_label.setStyleSheet("color: #ea9d59; font-size: 14px; font-family:'Roboto-Mono';")
            or_label.setGeometry(160,80,100,30)

            input_button = QPushButton('Select URL File', window)
            input_button.setGeometry(160, 120, 100, 30)
            input_button.clicked.connect(pdf_extract)
            input_button.setStyleSheet("QPushButton { background-color: #ea9d59; color: black; font-family: 'Roboto-Mono'; font-weight: bold;  border-radius: 10px;}")
            # input_button.clicked.connect(load_file)

            # Create the URL input box
            url_input = QLineEdit(window)
            url_input.setGeometry(10, 50, 380, 30)
            url_input.setStyleSheet("QLineEdit { background-color: black; border-radius: 15px; border: 1px solid #c8c8c8; font-size: 14px; font-family: 'Roboto Mono'; color: #ea9d59;}")
            url_input.setPlaceholderText("Enter URL")

            # Create the submit button
            submit_btn = QPushButton("Submit", window)
            submit_btn.setGeometry(300, 160, 80, 30)
            submit_btn.setStyleSheet("QPushButton { background-color: #ea9d59; color: black; font-weight: bold; font-family: 'Roboto-Mono'; border-radius: 10px;}")
            submit_btn.clicked.connect(on_submit_clicked)
            
            # Show the window
            window.show()
            sys.exit(app.exec_())
        # Initialize the Crawler instance
        _crawler.goToURL("https://www.google.com/")
        try:
            # Call the create_window function to start the GUI application
            create_window()
        except KeyboardInterrupt:
            print("\n[!] Ctrl+C detected, exiting gracefully.")
            exit(0)
