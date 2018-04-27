def attempt_adjust_earliest_start_date(order, newDate, earliest date list):
	if order is already earliest date:
		if order earliest date is before newDate: # if not then it will keep the later date
			set order earliest date to newDate
	else:
		add order to earliest date list with newDate
	return earliest date list

Save Starting Inventory for reference

# beginning of loop


# this loop will need to watch for a point when no orders can be scheduled due to lead times.
# make items discover their dependencies before finding earliest schedule dates
# so all of the dependencies will be worked out before this lead time issue comes up.


# if the last loop didn't end up in a schedule success, then add in
# an order called labor gap.  It will bump the attempted schedule date
# for the first order in to range of that orders earliest allowed schedule date.
while len(order priority) > 0:
	if scheduleSuccess == False:
		check first order earliest schedule date
		# or find all orders without dependencies and take the earliest allowed to scheduled of those.
		calculate expected labor gap for first orders production area
		add labor gap as a scheduled order for its production area
	orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess = function_below(orderPriority, scheduledOrders, unScheduledOrders)


# beginning of function_below()
scheduleSuccess = False
x = 0
while x < len(orderPriority):
	Check if starting inventory plus all scheduled orders results in any negatives:
		error out if true
	Get Order Priority (SOs then MOs on first loop)
	Check first pri order for earliest available schedule time according to labor group (probably Shipping on first loop)
	if the start date is before earliest allowed start date on earliest date list:
		move on to next priority order
		x+=1
	if there are any unscheduled dependencies on dependency list or any dependencies scheduled after current attempted date:
		move on to next priority order
		x+=1
	Make an Inventory Counter:
		Add all POs fulfilled by attempted start date
		Add all positive order lines already scheduled by attempted start date
		Subtract all negative order lines already scheduled, including any scheduled after attempted start date

	if first pri order makes any part negative based on Inventory Counter:
		shortage = parts and resulting negative quantities
		# need to resolve all make shortages before you start creating fake POs
		if there are shortages for make parts:
			# will need to add a section searching for existing orders here
			# just find where the orders cover the shortage then move their priorities up and set dependencies
			# then fake for whatever's left.
			# try this out:
			for each make shortage:
				mOrders = work orders where scheduled positive arrival in order of priority
				if len(mOrders) > 0:
					while shortage < 0:
						add first work order in mOrders to shortage
						place first work order priority just above current order in priority list
				if shortage < 0:
					create fake work order for shortage qty using BOM
					place fake work order priority just above current order in priority list
					add fake order to dependency list for current order
			scheduleSuccess = True
			return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess)
		# buy shortage time
		else:
			Lead time dates = earliest arrival based on lead time (if bought tomorrow) for all buy shortages
			for each buy shortage:
				pOrders = purchase orders where scheduled positive arrival date is after current schedule attempt date and before Lead time date
				if len(pOrders) > 0:
					if (sum of pOrders + shortage) is >= 0: # if the POs will cover the shortage
						while shortage < 0:
							shortage = add first pOrders qty to shortage
							set Lead time dates of part to first pOrders schedule date
							delete first line from pOrders
					else:
						shortage = shortage + sum of pOrders # shortage will still be negative and lead time is unaffected
			Longest lead time date = latest of the arrival dates in Lead time dates
			if Longest lead time date is after current attempt:
				attempt_adjust_earliest_start_date(order, Longest lead time date, earliest date list)
			else:
				create fake POs for all negative shortages and set their fulfillment dates equal to Longest lead time date
				schedule current order at current attempted date
				remove current order from priority list
			scheduleSuccess = True
			return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess)

	else:
		schedule first pri order
		remove first pri order from priority list
		scheduleSuccess = True
		return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess)
return (orderPriority, scheduledOrders, unScheduledOrders, scheduleSuccess)








"""
SO priority comes from Fishbowl?
MO priority comes from same.

Scheduling SO fulfillment requires some awareness of shipping labor available/required.
Set a value of labor required per line (either stored on part or product).
Use that to create a labor required total for each SO.
Then schedule SOs the same way as MOs but to Shipping's available labor.

Also, whenever an order is scheduled, add it to a list.
This will allow you to check what order it ended up using.

Consider error handling for missing BOMs and negative inventory (shouldn't happen when orders are scheduled).
Could avoid complicated BOMs missing tracking by creating a make parts missing BOMs list at the start.
At the end, just reference all parts fake ordered from that list for the total.

If you're trying to figure out how many loops it's going through,
use print(loopnumber, end='').  Should print on one line to make
it a bit more readable.

When you hit a necessary labor gap, add an order called labor gap.  At the end, you'll be
able to calculate how much labor gap was spent in each area.


"""
