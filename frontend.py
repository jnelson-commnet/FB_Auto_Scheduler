import pandas as pd
from tkinter import *
import numpy as np
from datetime import datetime, timedelta


def subtract_date(date, days):
    return (datetime.strptime(str(date)[:10], "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")


# Import Excel spreadsheets
missing_labour = pd.read_excel("data\missing.xlsx").drop_duplicates(subset="PART").sort_values("PART")
missing_BOM = pd.read_excel("data\missing.xlsx", sheet_name=1).drop_duplicates(subset="PART").sort_values("PART")
scheduled_orders = pd.read_excel(r"data\finalSchedule.xlsx", sheet_name=1).reset_index(drop=True)
scheduled_lines = pd.read_excel(r"data\finalSchedule.xlsx", sheet_name=2)
lead_times = pd.read_excel(r"data\finalSchedule.xlsx", sheet_name=6).reset_index(drop=True)
sales_orders = pd.read_excel(r"data\finalSchedule.xlsx", sheet_name=2).reset_index(drop=True)

# Sheet preprocessing
scheduled_orders["DATESCHEDULED"] = scheduled_orders["DATESCHEDULED"].apply(lambda x: str(x)[:10])
scheduled_lines["DATESCHEDULED"] = scheduled_lines["DATESCHEDULED"].apply(lambda x: str(x)[:10])
sales_orders["DATESCHEDULED"] = sales_orders["DATESCHEDULED"].apply(lambda x: str(x)[:10])
scheduled_orders["LaborRequired"] = scheduled_orders["LaborRequired"].apply(lambda x: float(x))

scheduled_lines = scheduled_lines[scheduled_lines["ORDERTYPE"] == "Finished Good"]
scheduled_orders["PART"] = np.nan
sales_orders = sales_orders[sales_orders["ITEM"] == "Phantom"]
sales_orders = sales_orders[sales_orders["ORDERTYPE"] == "Purchase"]
sales_orders["LeadTimes"] = np.nan

# Assign the finished good part number to each order
for i in scheduled_orders.index.tolist():
    try:
        scheduled_orders.loc[i, "PART"] = scheduled_lines[scheduled_lines["ORDER"] ==
                                                          scheduled_orders.loc[i, "ORDER"]]["PART"].tolist()[0][:25]

    except (KeyError, IndexError):
        scheduled_orders.loc[i, "PART"] = "NaN"

# Assign lead times to each part
for i in sales_orders.index.tolist():
    try:
        sales_orders.loc[i, "LeadTimes"] = lead_times[lead_times["PART"] ==
                                                      sales_orders.loc[i, "PART"]]["LeadTimes"].tolist()[0]
        sales_orders.loc[i, "PART"] = sales_orders.loc[i, "PART"][:25]

    except (KeyError, IndexError):
        scheduled_orders.loc[i, "PART"] = "10"

sales_orders.fillna("10", inplace=True)
sales_orders["Fulfillment Date"] = sales_orders["DATESCHEDULED"]
sales_orders["Order Date"] = np.nan

# Calculate order dates
for i in sales_orders.index.tolist():
    sales_orders.loc[i, "Order Date"] = subtract_date(sales_orders.loc[i, "Fulfillment Date"],
                                                      int(sales_orders.loc[i, "LeadTimes"]))

# Rename columns
sales_orders = sales_orders[["Order Date", "Fulfillment Date", "PART", "QTYREMAINING"]].rename(
    columns={"PART": "Part", "QTYREMAINING": "Quantity"}
).sort_values("Order Date").reset_index(drop=True)

# Make list of manufacturing centers
mfg_centers = scheduled_orders.drop_duplicates(subset="MfgCenter").sort_values("MfgCenter").MfgCenter.tolist()
mfg_data = dict((i, None) for i in mfg_centers)

# Create a dictionary of dataframes for each center
for center in mfg_centers:
    mfg_data[center] = scheduled_orders[scheduled_orders["MfgCenter"]
                                        == center].reset_index(drop=True).drop(columns=["MfgCenter", "Priority"])
    mfg_data[center].rename(columns={"DATESCHEDULED": "Date Scheduled",
                                     "ORDER": "Order",
                                     "PART": "Part",
                                     "LaborRequired": "Labour Required"}, inplace=True)

# Start building the GUI
master = Tk()
master.title("Auto Schedule")


# The basic page class
class Page(Frame):
    def __init__(self, *args, **kwargs):
        Frame.__init__(self, *args, **kwargs)

    def show(self):
        self.lift()


# Create labour page template
class Labour(Page):
    def __init__(self, *args, df, title, **kwargs):
        Page.__init__(self, *args, **kwargs)
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Text(self, yscrollcommand=scrollbar.set)
        listbox.insert(END, title + "\n----------------------\n")

        for item in df["PART"]:
            listbox.insert(END, item + "\n")

        listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar.config(command=listbox.yview)
        listbox.config(state=DISABLED)


# Create bill of materials page template
class BOM(Page):
    def __init__(self, *args, df, title, **kwargs):
        Page.__init__(self, *args, **kwargs)
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Text(self, yscrollcommand=scrollbar.set)
        listbox.insert(END, title + "\n----------------------\n")

        for item in df["PART"]:
            listbox.insert(END, item + "\n")

        listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar.config(command=listbox.yview)
        listbox.config(state=DISABLED)


# Create general template for manufacturing centers
class Template(Page):
    def __init__(self, *args, df, title, **kwargs):
        Page.__init__(self, *args, **kwargs)
        scrollbar = Scrollbar(self)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = Text(self, yscrollcommand=scrollbar.set)

        listbox.insert(END, title + "\n----------------------\n")
        listbox.insert(END, df.to_string(header=True))

        listbox.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar.config(command=listbox.yview)
        listbox.config(state=DISABLED)


page_dict = {}
container = Frame(master)
menu_bar = Frame(master)

# Create labour, bom, and sales pages
labour = Labour(master, df=missing_labour, title="Labour")
bom = BOM(master, df=missing_BOM, title="Bill of Materials")
sales = Template(master, df=sales_orders, title="Purchasing")

labour.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
bom.place(in_=container, x=0, y=0, relwidth=1, relheight=1)
sales.place(in_=container, x=0, y=0, relwidth=1, relheight=1)

button_labour = Button(menu_bar, text="Labour", command=labour.lift)
button_bom = Button(menu_bar, text="BOM", command=bom.lift)
button_sales = Button(menu_bar, text="Purchasing", command=sales.lift)

button_labour.pack(side="left")
button_bom.pack(side="left")
button_sales.pack(side="left")

# Create mfg center pages
for center in mfg_centers:
    page_dict[center] = [Template(master, df=mfg_data[center], title=center), None]
    page_dict[center][1] = Button(menu_bar, text=center, command=page_dict[center][0].lift)
    page_dict[center][0].place(in_=container, x=0, y=0, relwidth=1, relheight=1)
    page_dict[center][1].pack(side="left")

# Populate master frame
menu_bar.pack(side="top", fill="x", expand=False)
container.pack(side="top", fill="both", expand=True)
master.wm_geometry("800x600")

mainloop()
