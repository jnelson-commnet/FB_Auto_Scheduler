import pandas as pd
import numpy as np
import ast


def dependencies():
    def string_to_list(se):
        temp = []
        for i in se:
            li = ast.literal_eval(str(i))
            temp.append([n.strip() for n in li])

        return temp

    order_data = pd.read_excel("finalSchedule.xlsx", dtype=str,
                               sheet_name="scheduledLines").drop(
        labels=["ITEM", "ORDERTYPE", "PART", "QTYREMAINING"], axis=1).drop_duplicates(subset="ORDER").set_index("ORDER")

    line_data = pd.read_excel("finalSchedule.xlsx", dtype=str,
                              sheet_name="scheduledLines")

    inventory = pd.read_excel("finalSchedule.xlsx", dtype=object, sheet_name="inventoryCounter")
    starting_inventory = inventory[inventory["ORDERTYPE"] == "Starting Inventory"]
    starting_inventory = starting_inventory[starting_inventory["INV"] != 0].drop(labels=["QTYREMAINING", "PARENT"],
                                                                                 axis=1).reset_index(drop=True)

    for index, row in starting_inventory.iterrows():
        starting_inventory.loc[index, "ORDER"] = "I" + "0" * (4 - len(str(index))) + str(index)

    for index, row in inventory.iterrows():
        if row["ORDERTYPE"] == "Starting Inventory":
            inventory.loc[index, "QTYREMAINING"] = row["INV"]
            if row["INV"] != 0:
                inventory.loc[index, "ORDER"] = \
                    starting_inventory[starting_inventory["PART"] == row["PART"]]["ORDER"].tolist()[0]

    inventory.fillna("NONE", inplace=True)
    inventory = inventory[inventory["ORDER"] != "NONE"]

    inventory.to_excel("inventory.xlsx")
    starting_inventory.to_excel("startingInventory.xlsx")

    inventory = pd.read_excel("inventory.xlsx", dtype=object)
    starting_inventory = pd.read_excel("startingInventory.xlsx", dtype=object)

    finished_goods = line_data[line_data["ORDERTYPE"] == "Finished Good"]
    purchased_goods = line_data[line_data["ORDERTYPE"] == "Purchase"]
    raw_goods = line_data[line_data["ORDERTYPE"] == "Raw Good"]
    sold_goods = line_data[line_data["ORDERTYPE"] == "Sale"]
    return_goods = line_data[line_data["ORDERTYPE"] == "SO Credit Return"]

    order_data["PRODUCED"] = np.nan
    order_data["CONSUMED"] = np.nan
    order_data = order_data.astype(object)

    for i in order_data.index.tolist():
        try:
            order_data.at[i, "PRODUCED"] = finished_goods[finished_goods["ORDER"] ==
                                                          i]["PART"].tolist()
        except (KeyError, IndexError):
            pass
        try:
            order_data.at[i, "PRODUCED"] += purchased_goods[purchased_goods["ORDER"] ==
                                                            i]["PART"].tolist()
        except (KeyError, IndexError):
            pass
        try:
            order_data.at[i, "PRODUCED"] += return_goods[return_goods["ORDER"] ==
                                                         i]["PART"].tolist()
        except (KeyError, IndexError):
            pass
        try:
            order_data.at[i, "CONSUMED"] = raw_goods[raw_goods["ORDER"] ==
                                                     i]["PART"].tolist()
        except (KeyError, IndexError):
            pass
        try:
            order_data.at[i, "CONSUMED"] += sold_goods[sold_goods["ORDER"] ==
                                                       i]["PART"].tolist()
        except (KeyError, IndexError):
            pass

    order_data = order_data.reset_index()

    for index, row in starting_inventory.iterrows():
        order_data = order_data.append({"ORDER": row["ORDER"],
                                        "DATESCHEDULED": row["DATESCHEDULED"],
                                        "PRODUCED": [row["PART"]], "CONSUMED": []}, ignore_index=True)

    order_data.set_index("ORDER")

    order_data.to_excel("OrderData.xlsx")

    order_data = pd.read_excel("OrderData.xlsx", dtype=str).set_index("ORDER")
    order_data[["PRODUCED", "CONSUMED"]] = order_data[["PRODUCED", "CONSUMED"]].apply(string_to_list)

    part_data = pd.DataFrame()
    part_data["PART"] = np.nan
    part_data["ORDER"] = np.nan
    part_data["DATE"] = np.nan
    part_data["QUANTITY"] = np.nan
    part_data.set_index("PART")

    for index, row in order_data.iterrows():
        for part in row["PRODUCED"]:
            part_subset = inventory[inventory["PART"] == part]
            quantity = part_subset[part_subset["ORDER"] == index]["QTYREMAINING"].tolist()
            if sum(quantity) == 0:
                quantity = abs(quantity[0])
            else:
                quantity = sum(quantity)
            part_data = part_data.append({"PART": part,
                                          "ORDER": index,
                                          "DATE": row["DATESCHEDULED"],
                                          "QUANTITY": float(quantity)}, ignore_index=True)

    part_data.to_excel("FinishedGoods.xlsx")

    part_data = pd.read_excel("FinishedGoods.xlsx", dtype=object)
    mfg_data = pd.read_excel("finalSchedule.xlsx", dtype=str, sheet_name="scheduledOrders").drop(
        labels=["DATESCHEDULED", "LaborRequired", "Priority"], axis=1).set_index("ORDER")

    columns = ["PARENTS", "CHILDREN", "START", "DURATION", "PROJECT", "RESOURCE"]

    dependencies = pd.DataFrame(columns=columns, index=order_data.index)

    columns = ["PART", "ORDER", "QUANTITY", "CHILD", "INFO"]

    dependency_lines = pd.DataFrame(columns=columns)

    for row in dependencies.loc[dependencies["CHILDREN"].isnull(), 'CHILDREN'].index:
        dependencies.at[row, 'CHILDREN'] = []
    for row in dependencies.loc[dependencies["PARENTS"].isnull(), 'PARENTS'].index:
        dependencies.at[row, 'PARENTS'] = []

    for index, row in order_data.iterrows():
        if row["CONSUMED"] != []:
            quantities = {}
            children = []
            for part in set(row["CONSUMED"]):
                line_dict = {}
                line_dict["PART"] = part
                line_dict["ORDER"] = index
                quantity = inventory[(inventory["PART"] == part) &
                                     (inventory["ORDER"] == index) &
                                     (inventory["QTYREMAINING"] < 0)]["QTYREMAINING"].tolist()

                quantity = abs(float(sum(quantity)))
                quantities[part] = quantity
                while quantity > 0:
                    part_index = part_data[(part_data["PART"] == part) & (part_data["QUANTITY"] > 0)].index.values
                    candidates = part_data.loc[part_index, "ORDER"].tolist()

                    best_date = "2200-10-10"
                    best_candidate_index = 0
                    for i in range(len(candidates)):
                        date_string = order_data[order_data.index == candidates[i]]["DATESCHEDULED"].tolist()[0][:10]
                        if date_string < best_date:
                            best_date = date_string
                            best_candidate_index = i

                    stock_before = part_data.loc[part_index[best_candidate_index], "QUANTITY"]
                    part_data.loc[part_index[best_candidate_index], "QUANTITY"] -= quantity
                    remaining = part_data.loc[part_index[best_candidate_index], "QUANTITY"]

                    if remaining < -0.0001:
                        line_dict["QUANTITY"] = stock_before
                        quantity = abs(remaining)
                        part_data.loc[part_index[best_candidate_index], "QUANTITY"] = 0
                    else:
                        line_dict["QUANTITY"] = quantity
                        quantity = 0
                    children.append(candidates[best_candidate_index])
                    line_dict["CHILD"] = candidates[best_candidate_index]
                    dependency_lines = dependency_lines.append(line_dict, ignore_index=True)
            dependencies.at[index, "CHILDREN"] = children
            for child in children:
                dependencies.loc[child, "PARENTS"] = dependencies.loc[child, "PARENTS"] + [index]

            dependencies.loc[index, "RESOURCE"] = mfg_data.loc[index, "MfgCenter"]
        dependencies.loc[index, "DURATION"] = 1
        if index[0] == "I":
            dependencies.loc[index, "PROJECT"] = "Inventory"
        else:
            dependencies.loc[index, "PROJECT"] = "Main"

        date = row["DATESCHEDULED"]
        dependencies.loc[index, "START"] = date[:10]

    print(dependencies.to_string())
    writer = pd.ExcelWriter("dependencies.xlsx")
    dependencies.to_excel(writer, "sheet1")
    dependency_lines.to_excel(writer, "lineData")
    writer.save()
