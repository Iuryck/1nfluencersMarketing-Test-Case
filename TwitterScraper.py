from lib2to3.pgen2 import driver
import selenium
import webdriver_manager
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
import os
import time
from selenium.webdriver.common.by import By
import pandas as pd
import shutil
import ctypes
import tkinter as tk
import tkinter.ttk as ttk
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime as dt
from selenium.common.exceptions import *
import pickle
import json



class TwitterScraper():
    """Class to accomplished what is asked in the Practical Test. Webscrapes Twitter to get data on 50
    random profiles with more than 1k followers
    """    

    
    def __init__(self, user:str, password:str, username_or_phone:str):
        """Initializing the scraper, taking in user credentials to be able to access twitter

        :param user: username or email
        :type user: str
        :param password: account password
        :type password: str
        :param username_or_phone: username displayed on twitter or phone number
        :type username_or_phone: str
        """        
        self.user = user 
        self.password = password
        self.username_or_phone = username_or_phone

    def set_driver(self):
        """Creates a selenium webdriver instance for this class
        """        

        options = webdriver.ChromeOptions()
        options.add_argument("start-maximized")
        
        self.driver = webdriver.Chrome(ChromeDriverManager().install() , options=options)

    def wait_element_load(self, by:str, element:str):
        """Function to wait for an element to be displayed on the twitter page.
        Finds the element by the paramaters passed, just like webdriver.find_element()

        :param by: method of finding the element: class name, tag name, xpath, etc.
        :type by: str
        :param element: arguments for the element itself
        :type element: str
        """        

        #Infinite loop
        while True:
            
            try:
                '''
                Here the code checks if the element is NOT visible in the web page
                If it is visible, it throws a TimeoutException, thus breaking the loop when the element can be found.
                '''

                WebDriverWait(self.driver, 1).until_not(EC.visibility_of_element_located((by, element)))
                
            except TimeoutException:
                break



    def login(self):
        """
        Logs the user in his account, provided when instantiating the class
        """        

        #Sets driver    
        self.set_driver()

        #Accessing login page
        self.driver.get('https://twitter.com/i/flow/login')

        #Waiting for the input boxes to load
        self.wait_element_load('tag name', 'input')

        #Finding input box for email and writing the keys
        self.driver.find_element('tag name', 'input').send_keys(self.user)

        #Click the Next button
        self.driver.find_element('xpath','//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div/div[6]/div').click()

        #Wait for the next page to load
        self.wait_element_load('tag name', 'input')

        #The website might prompt a page about suspicious activity and request username or a phone number
        if self.driver.find_elements('tag name', 'span')[1].text == 'Enter your phone number or username':
            
            #Writes username or phone number to text input
            self.driver.find_element('tag name', 'input').send_keys(self.username_or_phone)
            
            #Clicks next and waits next page to load
            self.driver.find_element('xpath', '//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div/div/div/div').click()
            self.wait_element_load('name', 'password')
        
        #Writes password to text input
        self.driver.find_element('name', 'password').send_keys(self.password)
        
        #Clicks login button and waits page to load
        self.driver.find_element('xpath','//*[@id="layers"]/div/div/div/div/div/div/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div/div[1]/div/div/div/div').click()

        self.wait_element_load('xpath',  "//div[@aria-label='Timeline: Your Home Timeline']")

    def get_influencer_links(self):
        """Scrapes the connect page to get random profile links

        :return: list of links found in the connect page
        :rtype: list
        """        
        
        #Going to connect people page to find people
        self.driver.get('https://twitter.com/i/connect_people')

        #Waiting for the feed to load
        self.wait_element_load('xpath',  "//div[@aria-label='Timeline: Connect']")

        

        #List to add profile links we find on this page
        influencer_links=[]

        def get_links():
            time.sleep(1)
            #Grabbing the feed of people as an element
            list_connect = self.driver.find_element('xpath',  "//div[@aria-label='Timeline: Connect']")

            #Grabbing all the divs that have the user profiles
            for profile_divs in list_connect.find_elements('xpath',  ".//div[@data-testid='UserCell']"):
                
                '''
                If there is a "user follows" text in a user cell, there will be 2 divs
                so we need to filter for that otherwise we will fail to get the data   
                '''
                divs = profile_divs.find_elements('xpath','./*')

                #If 1 div in cell
                if len(divs)==1:
                    #Finds user profile links accordingly
                    links = profile_divs.find_element('xpath','.//div/div[2]/div').find_elements('tag name','a')
                    for link in links:
                        link = link.get_attribute('href')
                        influencer_links.append(link)
                        

                #If 2 div in cell
                if len(divs)==2:
                    #Finds user profile links accordingly
                    links = profile_divs.find_element('xpath','.//div[2]/div/div[2]').find_elements('tag name','a')
                    for link in links:
                        link = link.get_attribute('href')
                        influencer_links.append(link)

        #Gets max distance we can scroll down on current page
        page_height = self.driver.execute_script("return document.body.scrollHeight")

        #Defining how much of this we want to scroll, can be divided for smaller scrolls
        scroll_height =  page_height/5

        #Gets current scroll height the algorithm is at
        scrolled = self.driver.execute_script("return window.pageYOffset + window.innerHeight")

        #Loops arbitrarily 5 times to get random profiles
        for _ in range(5):
            
            #Function to get links in current view
            get_links()

            #Scrolls down
            self.driver.execute_script(f"window.scrollTo(0, {scrolled + scroll_height});")

            #Stores how much has been scrolled
            scrolled = scrolled + scroll_height

            
            

        #Removes duplicates from list
        influencer_links = list(set(influencer_links))
        return influencer_links

    def get_influencer_page_data(self, profile_link:str):
        """Gets all the requested data from a users profile, given the link to 
        their profile

        :param profile_link: users profile link
        :type profile_link: str
        :return: users data inside a dictionary
        :rtype: dict
        """        

        
        #---- H E L P E R    F U N C T I O N S ---

        def transform_number_string(numbers:str):
            """transforms given text to real numbers

            :param numbers: number of followers replies or anything alike, in text
            :type numbers: str
            :return: the true number that text represents
            :rtype: float
            """            
            if ',' in numbers: numbers=numbers.replace(',','.')

            if 'M' in numbers:
                grade = 10**6
                numbers = float(numbers[:-1]) * grade
            elif 'K' in numbers:
                grade = 10**3
                numbers = float(numbers[:-1]) * grade

            elif len(numbers)==0:
                numbers=0.0
            else: numbers = float(numbers)

            return numbers

        def get_posts():
            """
            Reads the tweets displayed in the current user page.
            Skips Ads, Pinned tweets and Retweets, in other words, grabs
            only the users posts.
            """            
            time.sleep(2)
            timeline = self.driver.find_element('xpath',f"//div[starts-with(@aria-label, 'Timeline:')]")
            tweets = timeline.find_elements('xpath',f".//article[@data-testid='tweet']")
            

            for tweet in tweets:
                
                if len(tweets_dict)==10: continue

                #Get original users posts only
                if 'Retweeted' in tweet.get_attribute('innerHTML'):continue
                #Remove pinned tweets because it has more exposure than new tweets, causing bias
                if 'Pinned Tweet' in tweet.get_attribute('innerHTML'):continue
                
                replies = tweet.find_element('xpath',".//div[@data-testid='reply']").find_element('tag name', 'span').text
                replies = transform_number_string(replies)
                retweets = tweet.find_element('xpath',".//div[@data-testid='retweet']").find_element('tag name', 'span').text
                retweets = transform_number_string(retweets)
                likes = tweet.find_element('xpath',".//div[@data-testid='like']").find_element('tag name', 'span').text
                likes = transform_number_string(likes)

                #Only Promoted Tweets don't have post date
                try:
                    date = tweet.find_element('xpath',".//div[@data-testid='User-Names']").find_element('tag name',"time").get_attribute('datetime')
                    date = dt.datetime.fromisoformat(date[:-1] + '+00:00')

                except NoSuchElementException: 
                    continue

                tweet_id = tweet.find_element('tag name',"time").find_element('xpath','..').get_attribute('href').split('/')[-1]

                x={tweet_id: {'date':date,'likes':likes,'replies':replies,'retweets':retweets}}

                if len(tweets_dict)<10:

                    tweets_dict.update(x)             

        #-------------------------------------------   

        #Goes to the givven user profile
        self.driver.get(profile_link)

        #Waits for the username of said user to display on page
        self.wait_element_load('xpath',"//div[@data-testid='UserName']")

        #Gets the users displayed name, which is changeable
        user_name_divs = self.driver.find_element('xpath',"//div[@data-testid='UserName']").find_elements('tag name', 'span')
        displayed_name = user_name_divs[0].text

        #Gets the users user name, not changeable
        user_name = profile_link.split('/')[-1]

        #Gets the number of followers the user has
        followers = self.driver.find_element('xpath',f"//a[@href='/{user_name}/followers']").find_elements('tag name', 'span')[0].text

        #Transforms text to real numbers
        followers = transform_number_string(followers)

        #Asserting this profile has more than 1k followers
        try: assert followers>1000
        except AssertionError: AssertionError('User does not have more than 1k followers')

        #Gets the number of people the user follows
        following = self.driver.find_element('xpath',f"//a[@href='/{user_name}/following']").find_elements('tag name', 'span')[0].text

        #Transforms the text to real numbers
        following = transform_number_string(following)


        #Gets the date in which the user joined Twitter
        date_joined = self.driver.find_element('xpath',f"//span[@data-testid='UserJoinDate']").text.replace('Joined ','')
        
        #Transforms text to datetime
        date_joined = dt.datetime.strptime(date_joined, '%B %Y')

        #Gets a linked url in the user page, returns None if there is no url
        try: website = self.driver.find_element('xpath',f"//a[@data-testid='UserUrl']").find_elements('tag name', 'span')[0].text
        except NoSuchElementException: website=None
        

        '''
        Gets the users birthday, it might not be displayed, which throws the
        NoSuchElementException. It may also contain or not, the year of birth.
        If there is a year displayed, first attempt to transform the data will
        throw a ValueError which we can reat accordingly.
        '''
        try:
            #Gets birthday
            birthday = self.driver.find_element('xpath',f"//span[@data-testid='UserBirthdate']").text.replace('Born ','')
            #Tries to transform to datetime object
            birthday = dt.datetime.strptime(birthday, '%B %d')
        
        #Returns None if birthday is not displayed
        except NoSuchElementException: birthday=None
        
        #Returns datetime with Year if year is displayed
        except ValueError as e:
            if 'unconverted data remains' in str(e):
                birthday = dt.datetime.strptime(birthday, '%B %d, %Y')
            elif 'does not match format'  in str(e):
                birthday = dt.datetime.strptime(birthday, '%Y')


        #Gets the users profile description, returns None of description doesn't exist
        try: user_description = self.driver.find_element('xpath',f"//div[@data-testid='UserDescription']").find_element('tag name', 'span').text
        except: user_description = None



        #Creating dictionary to store the user tweets
        tweets_dict = {}

        #Waiting for user timeline to load
        self.wait_element_load('xpath',f"//div[starts-with(@aria-label, 'Timeline:')]")        
            
        #Gets max distance we can scroll down on current page
        page_height = self.driver.execute_script("return document.body.scrollHeight")

        #Defining how much of this we want to scroll, can be divided for smaller scrolls
        scroll_height =  page_height

        #Gets current scroll height the algorithm is at
        scrolled = self.driver.execute_script("return window.pageYOffset + window.innerHeight")
        
        
        #Looping until we get 10 tweets from the users page
        while len(tweets_dict)<10:
            get_posts()

            #Scrolls the page to the bottom of it, where more tweets will be loaded
            self.driver.execute_script(f"window.scrollTo(0, {scrolled + scroll_height});")

            #Stores the distance the algorithm has already scrolled
            scrolled = scrolled + scroll_height

        #---- ASSERTING DATA ----

        assert type(displayed_name) is str
        
        assert type(followers) is float

        assert type(following) is float
        
        #Not every user displayes their birthday
        assert (type(birthday) is dt.datetime) or (birthday is None)

        assert type(date_joined) is dt.datetime
        
        #Not every user displayes a description
        assert (type(user_description) is str) or (user_description is None)

        #Asserting we have 10 tweets
        assert len(tweets_dict)==10

        

        #Creating final dictionary with all the data requested
        user_data_dict = {

                'user_name':user_name,
                'displayed_name':displayed_name,
                'followers':followers,
                'following':following,
                'birthday':birthday,
                'date_joined':date_joined,
                'profile_description':user_description,
                'website':website,
                'posts_data':tweets_dict            
        }

        return user_data_dict
        

        


        

        
        

        

        
                    
            
            
                
            

        

try: os.mkdir('Output')
except FileExistsError:pass

credentials = json.load(open('config.json'))


tt = TwitterScraper(credentials['username'],credentials['password'], credentials['username_or_phonenumber'])
tt.login()
links = tt.get_influencer_links()
for link in links[:50]:
    
    try: data_dict = tt.get_influencer_page_data(link)
    except AssertionError as e:
        if str(e) == 'User does not have more than 1k followers':
            continue
        else: raise e

    posts_data = data_dict.get('posts_data')

    posts_dataframe = pd.DataFrame()

    for post_id in posts_data:
        df = pd.DataFrame(posts_data[post_id], index=[post_id])
        
        if posts_dataframe.empty:
            posts_dataframe = df
        else: posts_dataframe = pd.concat([posts_dataframe, df])
    
    username = data_dict.get("user_name")

    posts_dataframe.to_csv(f'Output\\{username}.csv')

    with open(f'Output\\{username}.pkl', 'wb') as dict2pkl:
        pickle.dump(data_dict, dict2pkl)

tt.driver.close()
tt.driver.quit()