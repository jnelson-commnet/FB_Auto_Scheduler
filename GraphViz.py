import pandas as pd
import csv
import gantt
import datetime
import math
from tkinter import *
import webbrowser
from tkinter import messagebox
from os.path import dirname, abspath
import ast

# Custom object to handle the order of nodes placed in gantt chart.
class Order:
    def __init__(self):
        self.list = []

    def add_left(self, value, i):
        self.list.insert(i, value)

    def add_right(self, value, i):
        self.list.insert(i + 1, value)


# Converts a comma seperated string to a python list.
# def cell_to_list(cell):
#     reader = csv.reader([str(cell)])
#     return_list = []
#     for row in reader:
#         for i in row:
#             return_list.append(i)
#     return return_list

def cell_to_list(i):
    li = ast.literal_eval(str(i))
    return [n.strip() for n in li]


# Extracts colors from graphviz.config and imports them.
def choose_color(item):
    with open("graphviz.config", "r") as file:
        reader = csv.reader(file)

        for row in reader:
            if row[0] == item:
                color = row[1]
                file.close()
                return color

        file.close()
        return "#ff16f3"


# Generates the gantt chart and saves it as an svg.
def generate_chart(df, start_date, end_date, save_file, input_root=None, max_depth=None):
    # Function to recursively define the order that nodes will be placed in
    def populate_order(value, current_depth):
        if max_depth:
            if current_depth == int(max_depth):
                return

        if node_data.loc[value, "CHILDREN"] == []:
            return

        else:
            children = node_data.loc[value, "CHILDREN"]
            for child in children:
                if children.index(child) + 1 <= math.ceil(len(children) / 2):
                    if child not in task_order.list:
                        task_order.add_left(child, task_order.list.index(value))
                        populate_order(child, current_depth + 1)

                else:
                    if child not in task_order.list:
                        task_order.add_right(child, task_order.list.index(value))
                        populate_order(child, current_depth + 1)

    gantt.define_font_attributes(fill='black',
                                 stroke='black',
                                 stroke_width=0,
                                 font_family="Verdana")

    # Import node data
    node_data = df
    node_data.replace(to_replace="nan", value="NONE", inplace=True)
    node_data["CHILDREN"] = node_data["CHILDREN"].apply(cell_to_list)
    node_data["PARENTS"] = node_data["PARENTS"].apply(cell_to_list)
    node_data["START"] = node_data["START"]

    project_list = node_data["PROJECT"].drop_duplicates().tolist()
    resource_list = node_data["RESOURCE"].drop_duplicates().tolist()
    roots = []

    # Find all root nodes
    for node in node_data.index:
        if node_data.loc[node, "PARENTS"] == []:
            roots.append(node)

    nodes = node_data.index.tolist()
    tasks = {}
    resources = {}
    projects = {}
    master_project = gantt.Project(name="Master Schedule")

    # Create resource objects
    for resource in resource_list:
        resources[resource] = gantt.Resource(name=resource)

    # Create project objects
    for project in project_list:
        projects[project] = gantt.Project(name=project)

    # Create task objects
    for node in nodes:
        datel = node_data.loc[node, "START"]
        year = int(datel[:4])
        month = int(datel[5:7])
        day = int(datel[8:10])
        tasks[node] = gantt.Task(name=node,
                                 start=datetime.date(year, month, day),
                                 duration=int(float(node_data.loc[node, "DURATION"])),
                                 resources=[resources[node_data.loc[node, "RESOURCE"]]],
                                 color=choose_color(node_data.loc[node, "RESOURCE"]))

    # Add dependencies to tasks
    for node in nodes:
        tasks[node].add_depends(depends_of=[tasks[i] if i != "NONE" else None for i in node_data.loc[node, "CHILDREN"]])

    task_order = Order()
    root_priority = []

    # If user selected a specific node to view, set it as the root
    if input_root:
        roots = [input_root]

    # Create a priority list of roots based off of number of child nodes
    for root in roots:
        root_priority.append([root, len(node_data.loc[root, "CHILDREN"])])

    root_priority = sorted(root_priority, key=lambda x: x[1], reverse=True)

    # Higher priority roots will be placed in chart first
    print("Arranging Nodes...\n=========================================")
    for root in root_priority:
        task_order.list.append(root[0])
        populate_order(root[0], 1)
        print("Node {} completed".format(root))

    # Rearrange roots according to their "center of mass" based off of child nodes
    print("Rearranging Roots...\n=========================================")
    for root in roots:
        best_index = 0
        task_order.list.remove(root)
        best_dcount = len(task_order.list)
        for i in range(len(task_order.list)):
            count_left = 0
            count_right = 0
            for child in node_data.loc[root, "CHILDREN"]:
                count_left += task_order.list[:i].count(child)
                count_right += task_order.list[i:].count(child)

            dcount = abs(count_right - count_left)

            if dcount < best_dcount:
                best_dcount, best_index = dcount, i

        task_order.add_right(root, best_index)
        print("Root {} completed".format(root))

    # Assign tasks to projects
    for key in task_order.list:
        projects[node_data.loc[key, "PROJECT"]].add_task(tasks[key])

    master_project.add_task(projects["Main"])

    # Create svg
    master_project.make_svg_for_tasks(filename=save_file,
                                      start=start_date,
                                      end=end_date)


# The function called when submit button is pressed on gui.
def submit():
    try:
        # Pull information from entry fields
        start_date = start_date_entry.get()
        end_date = end_date_entry.get()
        root_node = root_order_entry.get()
        max_depth = max_depth_entry.get()
        file_name = file_name_entry.get() + ".svg"

        # Parse dates
        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%m/%d/%Y")
            start_date = datetime.date(start_date.year, start_date.month, start_date.day)

        else:
            start_date = None

        if end_date:
            end_date = datetime.datetime.strptime(end_date, "%m/%d/%Y")
            end_date = datetime.date(end_date.year, end_date.month, end_date.day)

        else:
            end_date = None

    except ValueError:
        messagebox.showinfo("Error", "Please enter a date in the provided format")
        return

    # Generate chart
    try:
        print("Generating chart...\n=============================================")
        generate_chart(pd.read_excel(r"dependencies.xlsx", dtype=str).set_index("ORDER"),
                       start_date, end_date, file_name, root_node, max_depth)

    except KeyError:
        messagebox.showinfo("Error", "Please enter a valid order number")
        return

    try:
        # Get path to GraphViz directory
        d = dirname(abspath(__file__))
        webbrowser.open(r"{}\{}".format(d, file_name))

        if not save_bool.get():
            # Clear entry fields
            start_date_entry.delete(0, "end")
            end_date_entry.delete(0, "end")
            file_name_entry.delete(0, "end")
            root_order_entry.delete(0, "end")
            max_depth_entry.delete(0, "end")

    except:
        messagebox.showinfo("Error", "Unable to open file. Make sure a default browser is installed.")


# The function called when search button is pressed on gui.
def search(event):
    display_box.config(width=80, state=NORMAL)

    # Reference global dataframe df, the contents to be displayed in the search box
    global df
    df = line_data[line_data["ORDER"] == search_bar_entry.get()]

    # display df
    if len(df["ORDER"].tolist()) > 0:
        display_box.delete(1.0, END)
        display_box.insert(END, df.to_string(header=True))

    if not search_bar_entry.get():
        df = line_data
        display_box.delete(1.0, END)
        display_box.insert(END, df.to_string(header=True))

    display_box.config(width=80, state=DISABLED)
    return


# The function called when a sort button is pressed on gui.
def sort(header):
    display_box.config(width=80, state=NORMAL)
    display_box.delete(1.0, END)
    display_box.insert(END, df.sort_values(header, ascending=sort_bool.get()).to_string(header=True))
    display_box.config(width=80, state=DISABLED)


# Set up master frame
master = Tk()
master.title("Gantt Chart Setup")

# These two frames sit side by side, config box handles chart generation and search box handles searching
config_box = Frame(master)
search_box = Frame(master)

# In the following section the config box is built
###############################################################################

container = Frame(config_box)
title = Frame(config_box)

# Labels for entry fields
Label(container, text="Start Date (MM/DD/YYYY)").grid(row=0, pady="2px", sticky="W")
Label(container, text="End Date (MM/DD/YYYY)").grid(row=1, pady="2px", sticky="W")
Label(container, text="File Name").grid(row=4, pady="2px", sticky="W")
Label(container, text="Root Order (leave blank for all orders)").grid(row=2, pady="2px", sticky="W")
Label(container, text="Max Depth (leave blank for infinite)").grid(row=3, pady="2px", sticky="W")
Label(title, text="Generate Chart", height=3).pack()

# Entry fields
start_date_entry = Entry(container)
end_date_entry = Entry(container)
root_order_entry = Entry(container)
max_depth_entry = Entry(container)
file_name_entry = Entry(container)

submit_button = Button(container, text="Submit", command=submit)

# Save options button
save_bool = IntVar()
save_box = Checkbutton(container, text="Save options", variable=save_bool)

# Populate container frame
start_date_entry.grid(row=0, column=1, pady="2px")
end_date_entry.grid(row=1, column=1, pady="2px")
root_order_entry.grid(row=2, column=1, pady="2px")
max_depth_entry.grid(row=3, column=1, pady="2px")
file_name_entry.grid(row=4, column=1, pady="2px")
save_box.grid(row=5, pady="2px")
submit_button.grid(row=5, column=1, pady="2px")

# In the following section the search box is built
#############################################################################

# Import line data
line_data = pd.read_excel(r"dependencies.xlsx", dtype=str, sheet_name="lineData").replace("nan", "NONE")
line_data["PART"] = line_data["PART"].apply(lambda x: x[:25])
line_data["QUANTITY"] = line_data["QUANTITY"].apply(lambda x: round(float(x), 3))

df = line_data

# Search bar
search_bar = Frame(search_box)
search_bar.grid(row=0, columnspan=8, sticky="W")
Label(search_bar, text="Order Detail Search:").pack(side="left")

# Sort bar
sort_bar = Frame(search_box)
sort_bar.grid(row=1, columnspan=8, sticky="W")
Label(sort_bar, text="Sort by: ").pack(side="left")
sort_bool = IntVar()
sort_order_up = Radiobutton(sort_bar, text="Ascending", variable=sort_bool, value=1)
sort_order_down = Radiobutton(sort_bar, text="Descending", variable=sort_bool, value=0)

# Create list of headers in line data
headers = list(line_data)
sort_buttons = {}

# Create sort buttons
for header in headers:
    sort_buttons[header] = Button(sort_bar, text=header, command=lambda h=header: sort(h))
    sort_buttons[header].pack(side="left")

sort_order_up.pack(side="left")
sort_order_down.pack(side="left")

display_box = Text(search_box, wrap=NONE)
display_box.grid(row=2, pady="2px", sticky=N + S + E + W)

# Scrollbar
xscrollbar = Scrollbar(search_box, orient=HORIZONTAL, command=display_box.xview)
xscrollbar.grid(row=3, sticky=W + E)
yscrollbar = Scrollbar(search_box, orient=VERTICAL, command=display_box.yview)
yscrollbar.grid(row=2, column=2, sticky=N + S)

search_bar_entry = Entry(search_bar)
search_button = Button(search_bar, text="Search", command=lambda: search("event"))

search_bar_entry.config(width=80)
search_bar_entry.pack(side="left", expand=True)
search_button.pack(side="left", padx="5")

title.pack(side="top", expand=False, pady="1px")
container.pack(side="top", expand=True, fill="y")

config_box.grid(row=0, column=0, padx="5px", pady="4px", sticky=N + S + E + W)
search_box.grid(row=0, rowspan=2, column=1, padx="5px", pady="5px", sticky=N + S + E + W)

# Allow searching with the press of enter key
search_bar_entry.bind("<Return>", lambda event: search(event=event))

mainloop()
