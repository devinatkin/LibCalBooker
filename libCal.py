import collections
import json
import os
import platform
import random
import string
from tkinter import messagebox
from tkinter import *
from tkinter.ttk import Progressbar
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import httplib2
import re
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# Configuration Variables
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'GenericApp'
USER_INFO_FILE = 'userInfo.json'
CREDENTIAL_DIR = os.path.expanduser('~/.credentials')
EMAIL_DOMAIN = os.getenv('EMAIL_DOMAIN', 'example.com')  # Configurable domain
BROWSER_CHOICES = ["Chrome", "Firefox"]
LIBRARY_URL = 'http://libcal.example.com/rooms_acc.php?gid=13445'  # Configurable URL
ROOMS = ['Room 1001', 'Room 1002', 'Room 1003', 'Room 1004']  # Configurable room list
TIME_SLOTS = ['8:00am - 8:30am', '8:30am - 9:00am', ...]  # Configurable time slots


class GUI:
    def __init__(self, master):
        self.version = 1.0
        self.master = master
        self.driver = None
        self.userInfo = self.load_user_info()
        self.setup_window()
        self.create_widgets()
        self.master.lift()

    def load_user_info(self):
        if os.path.exists(USER_INFO_FILE):
            with open(USER_INFO_FILE) as data_file:
                return json.load(data_file)
        else:
            default_user_info = {
                'version': self.version,
                'first': 'FirstName',
                'last': 'LastName',
                'email': f'user@{EMAIL_DOMAIN}',
                'override': 0,
                'confirm': 1,
                'browser': BROWSER_CHOICES[0],
                'firstLoad': True,
                'authEmail': ''
            }
            with open(USER_INFO_FILE, 'w') as data_file:
                json.dump(default_user_info, data_file)
            return default_user_info

    def setup_window(self):
        self.master.title(f"{APPLICATION_NAME} v{self.version}")
        self.master.resizable(False, False)
        self.master.protocol("WM_DELETE_WINDOW", self.window_close)
        self.master.bind('<Return>', self.submit_click)

    def create_widgets(self):
        # User Info
        Label(self.master, text="[ USER INFO ]", font=("Helvetica", 16, "bold")).grid(row=0, column=1, columnspan=2, sticky=E + W)
        self.create_user_entry_fields()
        
        # Browser Selection
        self.browserVal = StringVar(value=self.userInfo["browser"])
        OptionMenu(self.master, self.browserVal, *BROWSER_CHOICES).grid(row=4, column=2, sticky=W)
        
        # Room and Date Selection
        self.setup_date_selection()
        self.setup_room_selection()
        self.setup_time_selection()

        # Submit Button and Progress Bar
        self.submit = Button(self.master, text="Submit", command=self.submit_click)
        self.submit.grid(row=8, column=2, sticky=(N, S, E, W), padx=(0, 5), pady=(0, 5))
        self.submit["state"] = "disabled"
        self.loadingBar = Progressbar(self.master, orient=HORIZONTAL, length=100, mode='determinate')
        self.loadingBar.grid(row=9, column=2, sticky=(N, S, E, W), padx=(0, 5), pady=(0, 5))

        # Show welcome message if first load
        if self.userInfo["firstLoad"]:
            messagebox.showinfo("Welcome", "Update your [USER INFO] with your own name and email. Multiple room bookings are not supported.")

    def create_user_entry_fields(self):
        labels = ['First:', 'Last:', 'Email:']
        fields = ['first', 'last', 'email']
        for i, (label, field) in enumerate(zip(labels, fields), start=1):
            Label(self.master, text=label, font=("Helvetica", 12, "bold")).grid(row=i, column=1, sticky=W)
            entry = Entry(self.master)
            entry.grid(row=i, column=2, stick=E + W, padx=(0, 5))
            entry.insert(0, self.userInfo[field])
            setattr(self, f"{field}Entry", entry)

    def setup_date_selection(self):
        # Create a variable for the selected date
        self.chosenDate = StringVar(self.master)
        self.chosenDate.set("Select a Date")

        # Placeholder for available dates - replace with logic to fetch dates as needed
        self.availDates = ["Loading..."]  # Initial state before dates are loaded

        # Create a dropdown menu for date selection
        self.dateOptionMenu = OptionMenu(self.master, self.chosenDate, *self.availDates, command=self.date_click)
        self.dateOptionMenu.grid(row=0, column=0, columnspan=1, sticky=(N, S, E, W), pady=(8, 0), padx=(5, 0))

        # Assume dates are fetched from some source (e.g., a website)
        self.fetch_dates()

    def fetch_dates(self):
        # Example function to fetch dates, replace with real logic
        # This could involve scraping or using an API.
        self.availDates = ["2024-10-18", "2024-10-19", "2024-10-20", "2024-10-21"]  # Replace with dynamic fetching logic
        self.update_date_menu()

    def date_click(self, selected_date):
        """
        Handles the event when a date is selected from the dropdown menu.
        """
        # Update the selected date
        self.chosenDate.set(selected_date)
        
        # Optionally, print the selected date or perform other actions
        print(f"Selected date: {selected_date}")

        # Load available rooms and times for the selected date if needed
        self.load_available_times()


    def update_date_menu(self):
        # Update the date OptionMenu with the newly fetched dates
        menu = self.dateOptionMenu["menu"]
        menu.delete(0, "end")  # Clear the menu
        for date in self.availDates:
            menu.add_command(label=date, command=lambda d=date: self.date_click(d))
        # Set the default value to the first available date
        if self.availDates:
            self.chosenDate.set(self.availDates[0])


    def setup_room_selection(self):
        # Create a variable for the selected room
        self.chosenRoom = StringVar(self.master)
        self.chosenRoom.set("Select a Room")

        # Placeholder for available rooms - replace with dynamic fetching as needed
        self.availRooms = ROOMS  # ROOMS could be a predefined list or dynamically fetched

        # Create a dropdown menu for room selection
        self.roomOptionMenu = OptionMenu(self.master, self.chosenRoom, *self.availRooms, command=self.room_click)
        self.roomOptionMenu.grid(row=1, column=0, columnspan=1, sticky=(N, S, E, W), padx=(5, 0), pady=(5, 0))

        # Set the default room selection if rooms are available
        if self.availRooms:
            self.chosenRoom.set(self.availRooms[0])

    def room_click(self, selected_room):
        """
        Handles the event when a room is selected from the dropdown menu.
        """
        # Update the selected room
        self.chosenRoom.set(selected_room)
        
        # Optionally, print the selected room or perform other actions
        print(f"Selected room: {selected_room}")

        # Load available times for the selected room and date if needed
        self.load_available_times()


    def setup_time_selection(self):
        # Create the Listbox for time slots
        self.timeOptionList = Listbox(self.master, selectmode=EXTENDED, height=20, exportselection=0, takefocus=0)
        self.timeOptionList.grid(row=2, column=0, rowspan=200, columnspan=1, sticky=(N, S, E, W), padx=(5, 0), pady=5)
        self.timeOptionList.insert(0, "Loading available times...")
        self.timeOptionList.config(state=DISABLED)

        # Load available times based on selected room and date
        self.load_available_times()

    def load_available_times(self):
        # Example function to fetch available times, replace with real logic
        # This could involve scraping or using an API.
        self.timeOptionList.config(state=NORMAL)
        self.timeOptionList.delete(0, END)  # Clear previous entries

        # Placeholder for available times - replace with logic to fetch times
        self.availTimes = TIME_SLOTS  # TIME_SLOTS could be a predefined list or dynamically fetched
        for time_slot in self.availTimes:
            self.timeOptionList.insert(END, time_slot)

        # Disable the Listbox if no times are available
        if not self.availTimes:
            self.timeOptionList.insert(END, "No times available")
            self.timeOptionList.config(state=DISABLED)
        else:
            self.timeOptionList.config(state=NORMAL)


    def window_close(self):
        self.save_user_info()
        self.master.destroy()
        if self.driver:
            self.driver.quit()

    def save_user_info(self):
        self.userInfo.update({
            "first": self.firstEntry.get(),
            "last": self.lastEntry.get(),
            "email": self.emailEntry.get(),
            "browser": self.browserVal.get(),
            "firstLoad": False
        })
        with open(USER_INFO_FILE, 'w') as data_file:
            json.dump(self.userInfo, data_file)

    def submit_click(self, event=None):
        email = self.emailEntry.get().strip()
        if not email.endswith(f"@{EMAIL_DOMAIN}"):
            tkMessageBox.showerror("Email format error", f"Please use a valid @{EMAIL_DOMAIN} email address.")
            return
        # Other logic for submitting form
        pass


if __name__ == '__main__':
    root = Tk()
    libGui = GUI(root)
    root.mainloop()