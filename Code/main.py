#######################################################################################
#  BugetAnalyzer Application
#  Copyright (C) 2022 - 2023 Michael Dunlap
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License
#    http://www.gnu.org/licenses/gpl.txt
#  for more details.
#
#######################################################################################

# Kivy imports
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout 
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock

# Regular imports
import os
import re
import sys
import csv
import numpy as np
## Importing matplotlib causes problems if done here.
## We will put the import for matplotlib in the body
## of the graphing functions, as this does not seem to 
## cause problems.

PROJ_DIR = # TODO put the project directory here

class AccountExpenseHistory:
    """
    Represents an account's expense history in the program.

    Parses monthly account data and represents it with two fields:
        self.dates    : a list of strings giving the year and month in yyyy_mm format
        self.expenses : a list of lists of expenses, each index of self.expenses matches
                        the date in self.dates and contains a list of expenses for that
                        month as tuples (string: location, float: expense amount)

    NOTE: parse_and_aggregate_expenses and check_exclusion are meant to be overridden by 
          any subclass
    """
    
    p = re.compile("[1-9]+[0-9]*")
    
    def __init__(self, *, data_path, label):
        """" 
        Create an account expense history object

        Keyword arguments:
            data_path : a string giving the path to the monthly data for the account
            label     : a string giving the name to the account
        """

        self.label = label
        self.path = data_path

        self.files = self.extract_files()
        self.is_missing_data = self.audit_for_missing_data()
        self.dates = self.extract_dates()
        self.expenses = self.parse_and_aggregate_expenses()


    def extract_dates(self):
        """
        Gets the dates information from self.files
        """

        dates = []
        for file in self.files:
            y,m = map(int, self.p.findall(file))
            date_str = "{}_{:02d}".format(y,m)
            dates.append(date_str)
        return dates


    def extract_files(self):
        """
        Gets the names of the files from the data directory, skipping . files
        """

        os.chdir(self.path)
        data_files = []
        files = os.listdir()
        for file in files:
            if not file.startswith("."):
                data_files.append(file) 
        data_files.sort()
        return data_files
        

    def parse_and_aggregate_expenses(self):
        """
        Creates the list of lists for self.expenses

        Reads the files in self.path and converts them to a list of lists. 
        Each sublist contains a list of expenses for the corresponding month in self.dates. 
        Where the expenses are represented as (float : expense, string location) tuples.

        ASSERTION: The program assumes that expenses are all non-negative. 

        For example:
            if self.dates[0] == "2023_03"
            then the return of this function (which will be stored as self.expenses) should
            have a list of tuples representing expenses for March 2023 at index 0,
            where the tuples are of the form (float: expense, string: location).
        """

        date_idx     = 0
        expense_idx  = 1
        location_idx = 4

        data = []
        for file in self.files:
            month = []
            f = open(file, "r")
            r = csv.reader(f)
            for row in r:
                if row == []:
                    continue
                date     = row[date_idx]
                expense  = row[expense_idx]
                location = row[location_idx]
                location = location.upper()
                
                # get rid of commas
                expense = re.sub(",", "", expense)
                # expenses are negative so we convert
                expense = -1 * float(expense)

                is_excluded = self.check_exclusion(
                                date=date,
                                expense=expense,
                                location=location)

                if is_excluded:
                    continue
                else:
                    month.append( (expense, location) )
            f.close()
            data.append(month)
        return data


    def audit_for_missing_data(self):
        """
        Checks self.files for missing data
        """

        if self.files == []:
            return True 
        file0 = self.files[0]
        mo = self.p.findall(file0)
        if (len(mo) != 2):
            print("Error: files not formatted correctly in {}".format(self.path))
            print("exiting...")
            sys.exit(1)

        # start year and month of data
        y0,m0 = map(int, mo)
        for file in self.files[1: ]:
            mo = self.p.findall(file)
            if (len(mo) != 2):
                print("Error: files not formatted correctly in {}".format(self.path))
                print("Bad filename is {}".format(file))
                print("exiting...")
                sys.exit(1)
            y,m = map(int, mo)
            # update y0,m0 to the next month
            if m0 == 12:
                m0 = 1
                y0 += 1
            else:
                m0 += 1
            # check that y,m matches the next month
            if (y != y0 or m != m0):
                return True
        return False


    def check_exclusion(self, *, date, expense, location):
        """
        Checks exclusions rules expenses

        Method should be overridden in subclasses

        Keyword arguments:
            date     : a string giving the date of the expense. NOTE Depends on the format 
                       of the expense data file, varies from bank to bank.
            expense  : a float giving the expense ammount as it is in the original data file
            location : a string giving the location the expense corresponds to 

        Returns True if the expense should be ignored, otherwise False
        """ 
        
        return False

class ExpenseHistoryAnalyzer:
    """
    Parses one or more accounts based on a config file and can graph the results.
    """
    
    # Used to advertise to the app what graphing modes are supported
    available_graphing_modes = ["default", 
                                "multi-category",
 				"against-total",
    ]

    # Used to advertise to the app what modes require multiple selection 
    graphing_modes_requiring_multiselection = [
      "multi-category",
      "against-total",
    ]

    # output file used to check integrity of config file of any ExpenseHistoryAnalyzer
    output_path_regex_collisions = PROJ_DIR + os.path.sep + "Regex Collisions" + os.path.sep + "regex_collisions.txt"

    if (os.path.exists(output_path_regex_collisions)):
        os.remove(output_path_regex_collisions)

    def __init__(self, *, config_path, label, target_total_limit, intersect_account_dates = True, **accounts):
        """
        Sets the parameters for the analysis of one of more accounts

        Keyword arguments:
            config_path : a string representing the path to the config.txt file
            label: a string giving a name to the analyzer
            target_total_limit: float giving the target budget limit for all expenses 
            intersect_account_dates: if True, will use only the intersection of the
                                     self.dates fields in the accounts for analysis,
                                     if False, will use the union of those dates
            **accounts : one or more accounts AccountExpenseHistory objects, although more 
                         general use is intended. For example, ANY expense account object
                         with appropriately formatted fields self.dates and self.expenses
                         should work 
        ASSERTIONS: All accounts have had their self.dates fields sorted into chronological
                    order.
                    For all accounts, for all k, self.dates[k] is the date for the expenses 
                    found at self.expenses[k].
              
        """

        self.label = label
        self.config_path = config_path
        self.target_total_limit = target_total_limit
        self.accounts = accounts 

        cats, cat_limits = self.read_config()
        self.regex_category_dict = cats
        self.category_limits = cat_limits

        # Add the user defined cateogires 
        self.categories = list(cats.values())
        # Append the two special categories
        self.categories.append("Misc")
        self.categories.append("Total")

        if (intersect_account_dates):
            self.dates = self.find_date_range_intersection()
        else:
            self.dates = self.find_date_range_union()

        # initialize and setup output files for logging
        self.output_path_uncategorized = PROJ_DIR + os.path.sep + "Uncategorized Locations" + os.path.sep + self.label + "_uncategorized_locations.txt"

        f = open(self.output_path_uncategorized, "w")
        f.write("Using config file: {}\n".format(self.config_path))
        f.close()

        data = {}
        for account in accounts.values():
            d = self.categorize_history(account) 
            data[account.label] = d
        self.data = data


    def find_date_range_intersection(self):
        """ 
        Finds the intersection of the dates field over all accounts

        Returns the dates as a sorted list.
        
        ASSERTION: Sorting the date list will put them in chronological order
        """
        accounts = iter(self.accounts.values())
        account = next(accounts)
        date_range = set(account.dates)
        for account in accounts:
            date_range = date_range.intersection(set(account.dates))
        date_range = list(date_range)
        date_range.sort()
        
        return date_range


    def find_date_range_union(self):
        """
        Finds the union of the dates field over all accounts

        Returns the dates as a sorted list

        ASSERTION: Sorting the date list will put them in chronological order
        """

        date_range = set()
        for account in self.accounts.values():
            date_range = date_range.union(set(account.dates))
        date_range = list(date_range)
        date_range.sort()
        return date_range


    def graph(self, cats, mode):
        """ Wrapper function for all graphing modes """

        if mode == "default":
            self.graph_default(cats)

        elif mode == "multi-category":
            self.graph_multicategory(cats)

        elif mode == "against-total":
            self.graph_against_total(cats)

    
    def graph_default(self, category):
        """
        Graphs the monthly expenses for category, stacking each account in the graph.
        """

        from matplotlib import pyplot as plt
        plt.style.use('tableau-colorblind10')

        bottom = np.zeros(len(self.dates))
        fig, ax = plt.subplots()

        slice = {}
        for account in self.data.keys():
            slice[account]= self.data[account][category]


        for account, values in slice.items():
            p = ax.bar(self.dates, values, label = account,
                   bottom = bottom)
            bottom += values

        if category in self.category_limits.keys():
            ax.axhline(y=self.category_limits[category], color="red")
        
        plt.xticks(rotation=75)
        if len(self.data.keys()) > 1:
            ax.legend(loc="upper right")
        plt.show()

    def graph_multicategory(self, categories):
        """
        Graphs multiple categories, stacking each category. 
        """

        from matplotlib import pyplot as plt
        plt.style.use('tableau-colorblind10')
        bottom = np.zeros(len(self.dates))
        fig, ax = plt.subplots()

        slice = {}
        for category in categories:
            for account in self.data.keys():
                if (category not in slice.keys()):
                    slice[category] = self.data[account][category]
                else:
                    slice[category] = np.add(slice[category],self.data[account][category])

        for category, values in slice.items():
            p = ax.bar(self.dates, values, label = category,
                   bottom = bottom)
            bottom += values

        total_limit = 0
        for category in slice.keys():
            if category in self.category_limits.keys():
                total_limit += self.category_limits[category]
        ax.axhline(y=total_limit, color="red")
        
        plt.xticks(rotation=75)
        if len(categories) > 1:
            ax.legend(loc="upper right")
        plt.show()       
        

    def graph_against_total(self, categories):
        """
        Graphs the total then graphs the categories in front (stacked) for comparison. 
        """

        from matplotlib import pyplot as plt
        plt.style.use('tableau-colorblind10')
        bottom = np.zeros(len(self.dates))
        fig, ax = plt.subplots()

        totals = np.zeros(len(self.dates))
        for account in self.data.keys():
            totals = np.add(totals, self.data[account]["Total"])

        slice = {}
        for category in categories:
            for account in self.data.keys():
                if (category not in slice.keys()):
                    slice[category] = self.data[account][category]
                else:
                    slice[category] = np.add(slice[category],self.data[account][category])

        # plot totals first
        p = ax.bar(self.dates, totals, label="Total")

        # Plot other categories
        for category, values in slice.items():
            p = ax.bar(self.dates, values, label = category,
                   bottom = bottom)
            bottom += values

        total_limit = 0
        for category in slice.keys():
            if category in self.category_limits.keys():
                total_limit += self.category_limits[category]
        ax.axhline(y=total_limit, color="red")
        
        plt.xticks(rotation=75)
        ax.legend(loc="upper right")
        plt.show()       


    def categorize_history(self, account):
        """ 
        Categorizes the account expense history for an account. 

        If a location matches more than one category the first match will be used and
        the problematic location and configuration file will be written to 
        output_path_regex_collisions so that the user can modify the corresponding 
        config.txt file
        """

        category_expenses = {}
        for category in self.categories: 
            category_expenses[category] = [0] * len(self.dates)
        
        path = account.path
        os.chdir(path)
        uncategorized_locations = set()
        date_set = set(self.dates)
        data_idx = 0
        for a_idx in range(len(account.dates)):
            date = account.dates[a_idx]
            if date not in date_set:
                continue
            else:
                while (self.dates[data_idx] != date):
                    data_idx += 1
            month_data = account.expenses[a_idx]
            for expense,location in month_data:
                cats = []
                cat = None
                for regex in self.regex_category_dict.keys():
                    if regex.search(location):
                        cats.append(self.regex_category_dict[regex])
                if len(cats) > 1:
                    with open(self.output_path_regex_collisions, "a") as out:
                        out.write("Collision in {}\n".format(self.config_path))
                        out.write("Location: {} matches the following categories:\n".format(location))
                        for c in cats:
                            out.write(c + "\n")
                        out.write("\n")
                        

                if cats == []:
                    cat = "Misc"
                    uncategorized_locations.add(location)
                else:
                    cat = cats[0]

                category_expenses[cat][data_idx] += expense
                category_expenses["Total"][data_idx] += expense

        # Write the uncategorized locations before exiting
        with open(self.output_path_uncategorized, "a") as out:
            for location in uncategorized_locations:
                out.write(location + "\n")
        return category_expenses


    def read_config(self):
        """ 
        Reads in the configuration file. 

        Returns:
            limits_for_categories: dictionary key: string category 
                                              value: float budget limit for that category
            regex_category_dict : dictionary key: re.Pattern regex 
                                           value: string category

        Note: When parsing the data files, locations that match a key in regex_category_dict
              will be counted towards the category given by regex_category_dict[key].
              It is important that the locations only ever match at most one regex.
              (For details of how locations are categorized see categorize_history.)
        """

        category_idx = 0
        limit_idx    = 1
        regex_idx    = 2
        os.chdir(self.config_path)
        file = open("config.txt", "r")
        lines = file.readlines()
        file.close()
        regex_category_dict= {}
        limits_for_categories = {}
        for line in lines:
            line = line.strip().split("\t")
            try:
                regex=line[regex_idx]
                category=line[category_idx]
            except ValueError:
                print("Poblem with line")
                print(line)
                print("in file: {}".format(file))
                sys.exit(1)

            if category == "Total" or category == "Misc":
                print("Error: special categories Total and Misc are reserved")
                print("       and cannot be used in the configuration file.")
                print("Please correct the file at:")
                print(self.config_path)
                print("exiting...")
                sys.exit(1)
            p = re.compile(regex)
            regex_category_dict[p] = category

            if len(line) == 3:
                limit = float(line[limit_idx])
                limits_for_categories[category] = limit
        limits_for_categories["Total"] = self.target_total_limit 
  
        return (regex_category_dict, limits_for_categories)

class BudgetAnalyzerApp(App):
    """
    A program to help one assess their expenses and set reasonable budget limits.
    """

    def err_missing_data(self, dt):
        message = Label(text = self.paths_missing_data)
        popup = Popup( title = "WARNING Missing data in:",
                     content = message,
                   size_hint = (None, None), 
                       size = (400, 400))
        popup.open()


    def wrapper_source_refresh(self, spinner, text):
        self.analyzer = self.analyzers[text]
        self.refresh()


    def wrapper_mode_refresh(self, spinner, text):
        self.mode = text
        self.refresh()
    

    def refresh(self):
        app = App.get_running_app()
        source = app.analyzer
        self.body.clear_widgets()

        if (self.mode in self.modes_req_multislect):
            menu = GridLayout(cols=5)
            cats = self.analyzer.categories
            for cat in cats:
                btn = ToggleButton(text = cat,
                       background_color = (0.2,0.2,0.3,1))
                menu.add_widget(btn)

        else: 
            menu = GridLayout(cols=5)
            cats = self.analyzer.categories
            for cat in cats:
                btn = Button(text = cat,
                 background_color = (0.2,0.2,0.3,1))
                btn.bind (on_press = lambda x : source.graph(x.text, self.mode))

                menu.add_widget(btn)
            
        self.body.add_widget(menu)
        self.menu = menu

        self.footer.clear_widgets()
        if (self.mode in self.modes_req_multislect):
            btn = Button(text="Graph", pos_hint = {"center_x": .8}, size_hint = (0.3, 1)) 
            btn.bind(on_press = self.get_selection_and_graph)
            self.footer.add_widget(btn)


    def get_selection_and_graph(self, button):
        buttons = self.menu.children
        cats = []
        for btn in buttons:
            if btn.state == "down":
                cats.append(btn.text)
        self.analyzer.graph(cats, self.mode)
        

    def build(self):

        # Data paths 
        data_dir = PROJ_DIR + os.path.sep + "Data"
        # TODO add paths to data here 

        # Configuration paths
        config_dir = PROJ_DIR + os.path.sep + "Config"
        # TODO add configuration paths here
        
        # TODO create AccountExpenseHistory classes (or subclasses here) 

        # TODO add the AccountExpenseHistory objects to the tuple account_tuple
        account_tuple = ()
        
        # Check accounts for missing data
        self.paths_missing_data = ""
        for a in account_tuple:
            if a.is_missing_data:
                self.paths_missing_data += (a.path + "\n")

        # Analyzers
        # TODO create ExpenseHistoryAnalyzer objects here

        # TODO add the ExpenseHistoryAnalyzer objects to analyzer_tuple
        analyzer_tuple = ()


        self.analyzers = {a.label : a for a in analyzer_tuple} 

        self.modes = ExpenseHistoryAnalyzer.available_graphing_modes 
        self.modes_req_multislect = ExpenseHistoryAnalyzer.graphing_modes_requiring_multiselection

        # Set up the GUI
        main_view = BoxLayout(orientation="vertical")
        header = BoxLayout(orientation = "horizontal", 
                             size_hint = (0.5, 0.1))
        header.background_opacity = 1.0
        body   = BoxLayout(orientation = "vertical")
        
        footer = BoxLayout(orientation = "vertical", 
                             size_hint = (1, 0.3))

        # Set up header
        source_s = Spinner(text = list(self.analyzers.keys())[0],
                         values = self.analyzers.keys(),
                      size_hint = (0.4,1),
               background_color = (0,0,0,1))

        mode_s = Spinner(text=self.modes[0],
                         values = self.modes,
                         size_hint = (0.4, 1),
                    background_color = (0,0,0,1))

        header.add_widget(Label(text = "Source:", 
                           size_hint = (0.15,1)))
        header.add_widget(source_s)
        header.add_widget(Label(text = "Mode:", 
                           size_hint = (0.1,1)))
        header.add_widget(mode_s)

        self.mode = mode_s.text
        self.analyzer = self.analyzers[source_s.text]

        mode_s.bind(text=self.wrapper_mode_refresh)
        source_s.bind(text=self.wrapper_source_refresh)

        # Add header, body and footer to main_view
        main_view.add_widget(header)
        main_view.add_widget(body)
        main_view.add_widget(footer)
    
        # We save references to these for use in refresh
        self.body   = body
        self.footer = footer

        # Configures the body and footer based on 
        # self.analyzer and self.mode
        self.refresh()

        if self.paths_missing_data != "":
            Clock.schedule_once(self.err_missing_data, 1)
            
        return main_view

if __name__ == "__main__":
    BudgetAnalyzerApp().run() 
