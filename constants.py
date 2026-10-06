#######################
#       IMPORTS       #
#######################
from pandas import Series, read_csv, read_excel, DataFrame
from re import escape, search, sub
import calendar
from os import getcwd, makedirs
from os.path import exists, join
from numpy import ndarray
from pickle import dump, load
from datetime import datetime as dt
from math import pi
import matplotlib.pyplot as plt
from json import load as jload
from random import randint


#######################
#      CONSTANTS      #
#######################

#      MANAGERS     #
with open('manager_config.json', 'r') as f:
    manager_configs = jload(f)
with open('teams_config.json', 'r') as f:
    team_configs = jload(f)

#     BASE VALUES     #
emptyTask = None
home_dir = getcwd()
month_name_mapping = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December"
}
# currently required because the order is important, sadly
names_inf = read_csv('Anonymised Influence Data.csv')['Name'].tolist()
col_iter = 0

# PLACEHOLDER CLASSES #
class Employee:
    def __init__(self):
        pass
class Office:
    def __init__(self):
        pass

#       UNUSED      #
estimation_models = {
    "dev": {
        "Low": {
            "Story Points": [1, 2, 3, 5],
            "Number of new plugins to be developed": [0, 2],
            "Number of existing plugins to update": [1, 3],
            "Number of fields on the User Interface": {
                1: [0, 4],
                2: [5, 10],
                3: [11, 15],
                5: [16, 20]
            },
            "User interaction and workflow complexity": {
                "Forms": True,
                "Geometry": False,
                "Table": False
            },
            "Logic/Algorithmic Complexity (Estimated Lines of Code)": {
                1: [0, 50],
                2: [51, 100],
                3: [101, 150],
                5: [151, 200]
            },
            "Number of DDS Topics": [0, 1],
            "Number of DMAS APIs": {
                1: [0],
                2: [1],
                3: [2],
                5: [3]
            },
            "Number of messages exchanged with equipment": [1, 3]
        },
        "Medium": {
            "Story Points": [8, 13],
            "Number of new plugins to be developed": [3, 5],
            "Number of existing plugins to update": [4, 7],
            "Number of fields on the User Interface": {
                8: [21, 30],
                13: [31, 40]
            },
            "User interaction and workflow complexity": {
                "Forms": True,
                "Geometry": True,
                "Table": False
            },
            "Logic/Algorithmic Complexity (Estimated Lines of Code)": {
                8: [201, 350],
                13: [351, 500]
            },
            "Number of DDS Topics": [2, 5],
            "Number of DMAS APIs": {
                8: [4],
                13: [5, 6]
            },
            "Number of messages exchanged with equipment": [4, 6]
        },
        "High": {
            "Story Points": [21],
            "Number of new plugins to be developed": [6, float('inf')],
            "Number of existing plugins to update": [8, float('inf')],
            "Number of fields on the User Interface": {
                21: [41, float('inf')]
            },
            "User interaction and workflow complexity": {
                "Forms": True,
                "Geometry": True,
                "Table": True
            },
            "Logic/Algorithmic Complexity (Estimated Lines of Code)": {
                21: [501, float('inf')]
            },
            "Number of DDS Topics": [6, float('inf')],
            "Number of DMAS APIs": {
                21: [7, float('inf')]
            },
            "Number of messages exchanged with equipment": [7, float('inf')]
        }
    }
}

#######################
#       CLASSES       #
#######################
class Team:
    def __init__(self, name: str, manager: str, aliases: list = []) -> None:
        """
        Initializes a Team instance.

        Args:
            name (str): The name of the team.
            manager (str): The manager of the team.
            aliases (list, optional): A list of alternate names for the team. Defaults to an empty list.
        """
        self.nm = name
        self.alias = [self.nm.lower()] + [item.lower() for item in aliases]
        self.manager = manager
        self.resolved_items = None
        self.corresponding_aliases = None
        self.members = []
        self.tasks = []
        self.n_overdue = 0
        self.average_overdue_tasks = 0
    
    def assimilate(self, prospectives: list) -> list:
        """
        Finds entries in the given list that match any of the team's aliases.

        Args:
            prospectives (list): A list of strings or items to search through.

        Returns:
            list: A list of tuples. Each tuple contains the index of the matching entry and the matched alias.
        """
        indices = []
        for index in range(len(prospectives)):
            text = str(prospectives[index]).lower()
            for curr_alias in self.alias:
                pattern = r'\b' + escape(curr_alias) + r'\b'
                if search(pattern, text):
                    indices.append((index, curr_alias))
                    break
        return indices
    
    def set_overdue(self) -> None:
        """
        Find the number of overdue tasks in the team, and also calculates the average number of tasks due per employee running overdue
        """
        n = 0
        over_flag = False
        for emp in self.members:
            for task in emp.tasks:
                if task.overdue:
                    n += 1
                    if over_flag:
                        continue
                    over_flag = True
        self.n_overdue = n
        if over_flag:
            overdue_emps = len(self.overdue_employees())
            if overdue_emps != 0:
                self.average_overdue_tasks = self.n_overdue/overdue_emps
            else:
                self.average_overdue_tasks = 0
    
    def overdue_employees(self) -> list:
        """
        Returns a list of Employee objects that have tasks overdue

        Returns:
            list: Either empty (if no employees have overdue Tasks) or containing Employee objects with overdue Tasks
        """
        people = []
        for emp in self.members:
            if emp.n_overdue > 0:
                people.append(emp)
        if len(people) > 0:
            return people
        else:
            return []
    
    def show_data(self) -> None:
        """
        Prints out the name of the Team, the people working in it and all tasks associated with it
        """
        print(f"Name: {self.nm}\nPeople: {self.members}\nTasks: {self.tasks}")

class Task:
    def __init__(self, ref: int, subject: str, description:str, user_story: int, sprint: str, estimated_start: str, estimated_end: str, owner: list[str, str], assigned_to: str, status: str, is_closed: bool, created: str, modified: str, is_issue: bool = False) -> None:
        """
        Initialises a Task instance.

        Args:
            ref (int): Reference number of the function
            subject (str): Brief of the function
            description (str): Details of the function
            user_story (int): ID of the User Story
            sprint (str): Sprint name (including information on team, type of task and sprint number. Eg - ACAD Development 1)
            estimated_start (str): Date and time specified for start of sprint
            estimated_end (str): Date and time specified for end of sprint
            owner (list[str, str]): The Taiga User ID and Full Name of the sprint in-charge
            assigned_to (str): Full Name of the employee assigned to the function
            status (str): Task status (New, In Progress, Under Review, Completed, Blocked)
            is_closed (bool): Whether function is closed
            created (str): Date and time the function was created as a task in Taiga (to be taken as start date)
            modified (str): Date and time of last update to function in Taiga
            is_issue (bool): Whether the given task is from the Issues data
        """
        self.ref = ref
        self.sub = subject
        self.desc = description
        self.us = user_story
        self.sprint = sprint
        self.est_st = estimated_start
        self.est_end = estimated_end
        self.owner = owner
        self.emp = assigned_to
        self.status = status
        self.closed = is_closed
        self.start = created
        self.mod = modified
        self.is_issue = is_issue
        self.end = False
        self.due = False
        self.effort = None
        self.overdue = False
        self.employee = None
        self.us_order = None
        self.tb_order = None
        self.id = None
    
    def priority(self) -> int:
        """
        Gives the overall priority of a function as the product of the User Story order and Taskboard order

        Returns:
            int: Product of User Story order and Taskboard order
        """
        if self.is_issue:
            return 1
        return (self.us_order * self.tb_order)
    
    def add_demerits(self, emp: Employee) -> None:
        """
        Takes an Employee object and calculates demerits (lack of prioritisation score) to be added to it

        Args:
            emp (Employee): Employee object demerits are to be added to
        """
        priority = self.priority()
        priorities = emp.priorities()
        demerits = []
        empTasksIndices = priorities[0][0]
        empTasksPriorities = priorities[0][1]
        closedStatus = priorities[1]
        for idx in range(len(empTasksIndices)):
            item = empTasksIndices[idx]
            itemPriority = empTasksPriorities[idx]
            if (itemPriority > priority) & (closedStatus[idx]):
                demerits.append(itemPriority)
            if len(demerits) > 0:
                priorityDelta = demerits.copy()
                for idx in range(len(priorityDelta)):
                    priorityDelta[idx] = priorityDelta[idx] - priority
                    maxPriority = max(priorityDelta)
                    minPriority = min(priorityDelta)
                for idx in range(len(priorityDelta)):
                    currPDelta = priorityDelta[idx]
                    priorityDelta[idx] = normalise(currPDelta, maxPriority, minPriority)
                lackOfPrioritisation = 0
                for i in demerits:
                    lackOfPrioritisation += i
                emp.prioritisation += lackOfPrioritisation

class Employee:
    def __init__(self) -> None:
        """
        Initialises an Employee instance
        """
        self.nm = None
        self.team = None
        self.tasks = []
        self.prioritisation = 0
        self.team_object = None
        self.n_overdue = 0
        self.adjusted_prioritisation = 0
        self.influence_data = None
    
    def relativeTaskRank(self, task: Task, tf: bool = False) -> list[dict, dict, dict] | int | list[dict, dict, float]:
        """
        Returns a relative rank of a Task object amongst Tasks assigned to the Employee, either as a list of dictionaries (Task -> Priority) or as the index of the Task object in the Empoyee tasks list

        Args:
            task (Task): Task object assigned to the Employee
            tf (bool): Whether to return the absolute rank or the tasks higher in priority than the Task object, lower in priority that the Task object and those not yet done by the Employee
        
        Returns:
            
            int | list: list of dictionaries (Task -> Priority) or absolute rank of Task object or list of dictionaries (Task -> Priority) and float (infinite)
        """
        high = {}
        low = {}
        for item in self.tasks:
            if item == task:
                continue
            elif item.priority() > task.priority():
                high[item] = item.priority()
            else:
                low[item] = item.priority()
        highDone = {}
        lowDone = {}
        notDone = {}
        for key in high.keys():
            if high[key].closed:
                highDone[key] = high[key].priority()
            else:
                notDone["high"][key] = high[key].priority()
        for key in low.keys():
            if low[key].closed:
                lowDone[key] = low[key].priority()
            else:
                notDone[key]["low"] = low[key].priority()
        if tf:
            return [highDone, lowDone, notDone]
        else:
            return len(highDone) + 1
        return [high, low, float('inf')]
    
    def priorities(self) -> tuple[list[Task], list[Task]]:
        """
        Returns a tuple containing the sorted keys and value of the priorities dictionary (containing Task objects assigned to the Employee) and a list of Task objects completed by the Employee

        Returns:
            tuple: Tuple containing lists with sorted prioritiy dictionary keys and values, and Tasks completed by the Employee
        """
        priorities = {}
        done = []
        for item in self.tasks:
            priorities[item] = item.priority()
            done.append(item.closed)
        return (dicSort(priorities), done)
    
    def set_overdue(self) -> None:
        """
        Sets the Employees n_overdue value to the number of Task objects overdue for the Employee
        """
        n = 0
        for task in self.tasks:
            if task.overdue:
                n += 1
        self.n_overdue = n
    
    def set_prioritisation(self, maxVal: int, minVal: int) -> None:
        """
        Sets the Employees adjusted_prioritisation value

        Args:
            maxVal (int): Maximum normalised prioritisation value
            minVal (int): Minimum normalised prioritisation value
        """
        self.adjusted_prioritisation = maxVal - normalise(self.prioritisation, maxVal, minVal)
    
    def show_data(self) -> None:
        """
        Displays the Employees Name, Team and Task objects assigned
        """
        print(f"Name: {self.nm}\nTeam: {self.team}\nTasks: {self.tasks}")
    
    def inf_radar_chart(self, output_dir: str) -> None:
        """
        Plots radar chart for inlfuence data

        Args:
            output_dir (str): Directory where chart is saved
        """
        data = self.influence_data
        if not data:
            return
        labels = list(data.keys())
        values = list(data.values())
        values += values[:1]
        angles = [n/float(len(labels)) * 2 * pi for n in range(len(labels))]
        angles += angles[:1]
        fig, ax = plt.subplots(figsize = (7, 7), subplot_kw = dict(polar = True))
        ax.plot(angles, values, linewidth = 2, linestyle = 'solid', label = self.nm)
        ax.fill(angles, values, alpha = 0.3)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize = 8)
        ax.set_yticklabels([])
        ax.set_title(f"{self.nm} - Influence Radar", size = 12, pad = 20)
        file_name = join(output_dir, f"{self.nm} Influence Radar.png")
        plt.tight_layout()
        plt.savefig(file_name)
        plt.close()

class Office:
    def __init__(self, name: str) -> None:
        """
        Initialises an Office instance

        Args:
            name (str): Name of the Office
        """
        self.nm = name
        self.teams = []
        self.employees = []
        self.tasks = []
        self.run_number = 1
        self.influence_max = None
        self.bridging_max = None
        self.diffusion_speed_max = None
        self.admin_expertise_max = None
        self.holistic_social_positioning_max = None
        self.hub_like_max = None
        self.knowledge_seeking_max = None
        self.supportive_index_max = None
        self.tech_helping_max = None
        self.composite_influence_max = None
        self.bottleneck_potential_max = None
        self.self_reliance_max = None
        self.facilitation_max = None
        self.passiveness_max = None
        self.load_max = None
        self.influence_efficiency_max = None
        self.leadership_index_max = None
    
    def save(self) -> None:
        """
        Saves the Office object as a pickle binary file
        """
        with open('dat.pkl', 'wb') as f:
            for team in self.teams:
                for employee in team.members:
                    self.employees.append(employee)
                    for task in employee.tasks:
                        team.tasks.append(task)
                        self.tasks.append(task)
            self.run_number += 1
            self.set_overdue()
            dump(self, f)
    
    def load(self) -> Office:
        """
        Loads the Office object from a pickle binary file

        Returns:
            Office: The Office object being referenced
        """
        with open('dat.pkl', 'rb') as f:
            return load(f)
    
    def reset(self) -> None:
        """
        Resets all values in the Office object and saves
        """
        self.teams = []
        self.employees = []
        self.tasks = []
        self.run_number = 0
        self.save()
    
    def set_overdue(self) -> None:
        """
        Sets the overdue values for all Employee and Team objects in the Office
        """
        for employee in self.employees:
            employee.set_overdue()
        for team in self.teams:
            team.set_overdue()
    
    def show_data(self) -> None:
        """
        Displays the Team and Employee data for all such objects in the Office with a 5 second delay between each result
        """
        from time import sleep
        for team in self.teams:
            team.show_data()
            sleep(5)
        for employee in self.employees:
            employee.show_data()
            sleep(5)
    
    def set_tasks(self) -> None:
        """
        Populates the tasks list for each Team object as well as the Office
        """
        for team in self.teams:
            for employee in team.members:
                for task in employee.tasks:
                    team.tasks.append(task)
                    self.tasks.append(task)
    
    def remove_duplicates(self) -> None:
        """
        Removes duplicate entries
        """
        unique = []
        uniques = []
        for employee in self.employees:
            if employee.nm in uniques:
                continue
            uniques.append(employee.nm)
            unique.append(employee)
        self.employees = unique
        unique = []
        uniques = []
        for task in self.tasks:
            if task.ref in uniques:
                continue
            uniques.append(task.ref)
            unique.append(task)
        self.tasks = unique


#######################
#      FUNCTIONS      #
#######################

#       HELPER      #
def batch_index_delete(list_to_modify: list, indices: list = []) -> list:
    """
    Deletes elements from a list at the specified indices.

    Args:
        list_to_modify (list): The list to remove elements from.
        indices (list, optional): A list of indices to delete. Defaults to an empty list.

    Returns:
        list: The modified list with the specified elements removed.
    """
    for index in sorted(indices, reverse=True):
        del list_to_modify[index]
    return list_to_modify

def team_preprocessing(team_list: list) -> list:
    """
    Cleans a list of team names or text entries by removing non-alphabetic characters.

    Args:
        team_list (list): A list of strings to clean.

    Returns:
        list: A list of cleaned strings.
    """
    result = []
    for term in team_list:
        term = str(term)
        try:
            cleaned = sub(r'[^a-zA-Z ]+', '', term)
            result.append(cleaned)
        except Exception as e:
            print(e)
            result.append(term)
    return result

def date_data(dt: str) -> set | str:
    """
    Parses a date string and extracts components

    Args:
        dt (str): A date string to parse.

    Returns:
        set or str: A tuple of (day, month, year, month_name) if successful, otherwise an empty string if parsing fails.
    """
    if isinstance(dt, (list, tuple, Series, ndarray)):
        print("Date not in the right format")
        return ""
    try:
        dt = [int(dt[8:10]), int(dt[5:7]), int(dt[:4]), int(dt[5:7])]
        day = dt[0]
        month = dt[1]
        year = dt[2]
        month_name = month_name_mapping[dt[3]]
        return (day, month, year, month_name)
    except Exception as e:
        print(f"Error: {e}")
        return ""

def dicSort(dic: dict) -> list[list, list]:
    """
    Returns the sorted values and corresponding keys for a given dictionary

    Args:
        dic (dict): The dictionary to be sorted
    
    Returns:
        list: list containing a list of sorted keys and a list of sorted values for the dictionary
    """
    keys = list(dic.keys())
    vals = list(dic.values())
    sKeys = []
    sVals = []
    for i in range(len(keys)):
        val = min(vals)
        idx = vals.index(val)
        sVals.append(val)
        sKeys.append(keys[idx])
        keys.pop(idx)
        vals.pop(idx)
    return [sKeys, sVals]

def groupwise_division_dataset(dataset: str, output_folder: str, grouping_column: str, dataset_format: str = 'csv') -> None:
    """
    Saves data from the dataset as separate csv files, with the data grouped on the basis of a target column

    Args:
        dataset (str): Name of the dataset being grouped
        output_folder (str): Name of the folder where output CSVs are to be stored
        grouping_column (str): Name of the target column being used for grouping
        dataset_format (str): Format of the dataset (defaults to csv, can take xlsx)
    """
    if dataset_format == 'csv':
        df = read_csv(f"{dataset}.{dataset_format}")
    else:
        df = read_excel(f"{dataset}.{dataset_format}")
    if not exists(output_folder):
        makedirs(output_folder)
    grouped = df.groupby(f"{grouping_column}")
    for group, group_data in grouped:
        file_name = f"{group}.csv"
        file_path = join(output_folder, file_name)
        group_data.to_csv(file_path, index=False)

def groupwise_division_person(person: str, data: DataFrame, output_folder: str) -> None:
    """
    Saves data for a person into an individual CSV

    Args:
        person (str): Name of the Employee
        data (DataFrame): Data of the Employee
        output_folder (str): Name of the folder the CSV is to be saved
    """
    if not exists(output_folder):
        makedirs(output_folder)
    file_name = f"{person}.csv"
    file_path = join(output_folder, file_name)
    data.to_csv(file_path, index = False)

def normalise(val: int | float, ub: int | float, lb: int | float) -> float:
    """
    Returns a normalised value given the upper and lower bound

    Args:
        val (int | float): The value to be normalised
        ub (int | float): Upper bound of value
        lb (int | float): Lower bound of value
    
    Returns:
        float: Normalised value
    """
    if ub == lb:
        return 100
    return ((val - lb)/(ub - lb) * 100)

def now() -> str:
    """
    Gives the current date and time, formatted as 'DD-MM-YY at HH:MM:SS'

    Returns:
        str: Current date and time formatted as 'DD-MM-YY at HH:MM:SS'
    """
    now = str(dt.now())
    day = now[8:10]
    month = now[5:7]
    year = now[:4]
    time = now[11:19].replace(":", "-")
    return f"{day}-{month}-{year} at {time}"

def lower_list(val: str) -> str:
    """
    Returns the value in lowercase

    Args:
        val (str): String to be formatted
    
    Returns:
        str: val in lowercase
    """
    return val.lower()

def percent_max(val: int | float, maxVal: int | float) -> float:
    """
    Returns what percentage of the maximum value the given value is

    Args:
        val (int | float): Value to convert
        maxVal (int | float): The maxiumu value val can be
    
    Returns:
        float: Converted value
    """
    return (val/maxVal)*100

def crypt(value: str, key: int, encoding: bool) -> str:
    """
    Encodes or decodes values for anonymisation.

    Args:
        value (str): Value to encode/decode
        key(int): Key value for the encoding/decoding
        encoding(bool): Whether encoding (True) or decoding (False)
    
    Returns:
        str: Converted value
    """
    if not encoding:
        key *= -1
    temp = []
    res = ""
    for i in value:
        temp.append(chr(ord(i) + key))
    # for i in range(len(value)):
    #     idx = randint(0, len(temp) - 1)
    #     res += temp[idx]
    #     del temp[idx]
    return res

#        MAIN       #
def universal_date(date_data: tuple[int, int, int, str] | int, converting_to: bool = True, base_year: int = 2020) -> tuple[int] | tuple[int, int, int, str]:
    """
    Converts between a date tuple and the number of days since a base year.

    Args:
        date_data (tuple[int, int, int, str] or int): 
            If converting_to is True, a tuple (day, month, year, month_name).
            If converting_to is False, an integer representing the number of days since base_year.
        converting_to (bool, optional): 
            If True, converts a date to the number of days. If False, converts number of days back to a date. Defaults to True.
        base_year (int, optional): The base year for day calculations. Defaults to 2020.

    Returns:
        tuple: 
            If converting_to is True, returns a tuple with a single integer (days since base_year).
            If converting_to is False, returns a tuple (day, month, year, month_name).
    """
    def is_leap(yr):
        return yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)

    if converting_to:
        day, month, year, month_name = date_data
        days = 0
        for yr in range(base_year, year):
            days += 366 if is_leap(yr) else 365
        month_days = [31, 29 if is_leap(year) else 28, 31, 30, 31, 30,
                      31, 31, 30, 31, 30, 31]
        days += sum(month_days[:month - 1])
        days += day - 1
        return (days)
    else:
        total_days = date_data
        year = base_year
        while True:
            days_in_year = 366 if is_leap(year) else 365
            if total_days >= days_in_year:
                total_days -= days_in_year
                year += 1
            else:
                break
        month_days = [31, 29 if is_leap(year) else 28, 31, 30, 31, 30,
                      31, 31, 30, 31, 30, 31]
        month = 1
        for days_in_month in month_days:
            if total_days >= days_in_month:
                total_days -= days_in_month
                month += 1
            else:
                break
        day = total_days + 1
        month_name = calendar.month_name[month]
        return (day, month, year, month_name)

def col_add(df: DataFrame, dir_prop: list[tuple[list[int | float], float]] = [], inv_prop: list[tuple[int | float, float]] = [], col_name: str = None) -> None:
    """
    Adds a column to the given dataframe, with values being calculated as the product of all directly proportional values (weighted), divided by the product of inversely proportional values (weighted). If No column name is provided, it is named 'New Column No x', with x being set based on the col_iter variable.

    Args:
        df (DataFrame): Pandas DataFrame with the data being worked on
        dir_prop (list, optional): List containing tuples with columns with values that are directly proportional to the column being created, and their weights. Defaults to an empty list.
        inv_prop (list, optional): List containing tuples with columns with values that are inversely proportional to the column being created, and their weights. Defaultas to an empty list.
        col_name (str, optional): Name of the column to be added. Defaults to None.
    """
    global col_iter
    if not col_name:
        col_iter += 1
        col_name = f"New Column No {col_iter}"
    temp = []
    for idx in range(len(dir_prop[0][0] if dir_prop else inv_prop[0][0])):
        res = 1
        for col, wt in dir_prop:
            res *= col[idx] * wt
        for col, wt in inv_prop:
            temp0 = col[idx] * wt
            if temp0 == 0:
                pass
            else:
                res /= temp0
        temp.append(res)
    df[col_name] = temp

def give_inf_data(metric: list, message: str, parameter: str) -> str:
    """
    Returns the top 5 results per the given metric (column in data)

    Args:
        metric (list): A data column as a list
        message (str): What can be inferred from the metric
        parameter (str): Name given to the inferred value
    
    Returns:
        str: The top 5 results for the parameter value, formatted
    """
    result = ""
    temp = metric.copy()
    res = []
    _min = min(temp)
    _max = max(temp)
    for i in range(5):
        maxVal = max(temp)
        normVal = normalise(maxVal, _max, _min)
        idx = temp.index(maxVal)
        res.append((names_inf[idx], normVal))
        del temp[idx]
    result += f"\nThe following are the 5 {message} from the data (percentage of maximum):\n"
    for i in range(5):
        result += f"\t{i+1}. {res[i]
        [0]} ({parameter} Value - {round(res[i][1], 2)}%)\n"
    return result


#######################
#       OBJECTS       #
#######################
# the aliases and team names will have to be put into a configuration file
gen = Team('Gen', manager_configs["gen_manager"], team_configs['Gen'])
asw = Team('ASW', manager_configs["asw_manager"], team_configs['ASW'])
ew = Team('EW', manager_configs["ew_manager"], team_configs['EW'])
sw = Team('SW', manager_configs["sw_manager"], team_configs['SW'])
acad = Team('ACAD', manager_configs["acad_manager"], team_configs['ACAD'])
nav = Team('NAV', manager_configs["nav_manager"], team_configs['NAV'])
link = Team('LINK', manager_configs["link_manager"], team_configs['LINK'])
aaw = Team('AAW', manager_configs["aaw_manager"], team_configs['AAW'])
cmd = Team('CMD', manager_configs["cmd_manager"], team_configs['CMD'])
te = Team('TE', manager_configs["te_manager"], team_configs['TE'])
dmas = Team('DMAS', manager_configs["dmas_manager"], team_configs['DMAS'])
cms = Team('CMS', manager_configs["hod"], team_configs['CMS'])
emptyTask = Task(float('inf'), float('inf'), "Empty", "", float('inf'), float('inf'), "", "", "", "", "", False, "", "")


#######################
# OUTBOUND CONSTANTS  #
#######################
teams = [gen, asw, ew, sw, acad, nav, link, aaw, cmd, te, dmas, cms]
team_name_to_object = {
    'Gen': gen,
    'ASW': asw,
    'EW': ew,
    'SW': sw,
    'ACAD': acad,
    'NAV': nav,
    'LINK': link,
    'AAW': aaw,
    'CMD': cmd,
    'TE': te,
    'DMAS': dmas,
    'CMS': cms
}