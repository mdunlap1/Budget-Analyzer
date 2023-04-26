## Overview
This program reads monthly credit card or other expense account data and categorizes the expenses based on user defined categories. The user is then able to graphically view their expense history and assess it. The program is capable of handling multiple users and accounts. The user may toggle between different accounts in the main view, as well as select different graphing modes.

## Prerequisites
The user of this program will need a basic understanding of Python and a basic 
understanding of regular expressions. Additionally the user will need:
- Python     v3.7.3 or later
- Matplotlib v3.0.3 or later
- Numpy	     v1.16.2 or later
- Kivy       v2.0.0 or later

## Setup
0. Download the program folders and save them somewhere you intend to keep them. Then set up the PROJ_DIR in main.py and demo.py

1. For each account that you want to analyze make a folder in the Data directory.

2. Download the data, storing each month’s data in a separate file.

3. Make sure the naming convention for the monthly data obeys the following:
- The only numeric values in the name are the year and month
- The year preceeds the month in the name and the two are separated by non-numeric characters
- Lexicographically sorting the files is the same as chronologically sorting them

  As an example: cc_2023_03.csv is an acceptable name for the data from March 2023, 
  so long as all the other files for that account have the same prefix “cc_”.


4. Extend the AccountExpenseHistory class and override check_exclusion and parse_and_aggregate_expenses. 
   OR merely re-write them to fit your needs.

   The AccountExpenseHistory class takes two parameters,
   ```michael_expenses = AccountExpenseHistory (label = "michael", data_path = "michael_data_path")```
   The label is a string to identify the account with, the data_path is a string path to the 
   data directory for the account (a subdirectory of Data).

   The purpose of AccountExpenseHistory is to parse the user data and store it in an object for 
   use with an ExpenseHistoryAnalyzer object.

   The user needs to override this themselves because the manner in which the data is parsed will
   differ depending on the source.

5. The program can aggregate multiple accounts into a single analyzer, each analyzer needs a configuration file. 
   Make a directory for each analyzer in the Config folder.

6. Write a configuration file for each analyzer in a separate directory and save it as “config.txt”. 
   The config.txt file format is tab delimited with no header. Each row has a category_name, category_budget_limit 
   (monthly limit for category), and a regular expression that is used to match locations to the category_name. 
   Each row looks like this:

   [category_name]\t[category_budget_limit]\t[regex_to_identify_category]

7. Go to main.py and add in the data_paths, config_paths and set up your AccountExpenseHistory (or subclass thereof) 
   and ExpenseHistoryAnalyzer classes in build.

   The ExpenseHistoryAnalyzer class takes the folowing parameters:
   -label (a string giving the analyzer a name, used by the GUI)
   -target_total_limit (float representing a target total limit for expenses)
   -config_path (a string path to the directory containing the config.txt file)
   -intersect_account_dates (boolean, if True (default), the analyzer will only evaluate the intersection of the dates, if False the union)
   -one or more AccountExpenseHistory objects as labeled keyword arguments

8. Put all the AccountExpenseHistory objects into a tuple called accounts. This will enable the error check for missing data (gaps).

9. Put the ExpenseHistoryAnalyzers into a tuple called analyzers. This connects them to the GUI.

10. Run the program and check for:
- Missing data (which will display as a popup message)
- Uncategorized locations (which will show up in that directory)
- Regex collisions (instances of a location matching more than one regex.

11) Edit the configuration files and repeat steps 10 and 11 until the things are being categorized as desired.

## Demo
There are demo data and configuration files that can be used with demo.py.
The missing data for Graham is intentional and meant to demo how that condition is handled (with a popup).
