# FB_Auto_Scheduler

The goal of this project is to create an quick method of rescheduling production around variable requirements.  The earlier stages will use priority data to create an idealized schedule for the user.  That will expand to consider labor and inventory availability.  The next step will be comparing the newly created schedule to the one in FB.  That will then produce a list of changes necessary for the user to execute.  If possible, the final planned iteration would also execute the changes without user intervention.


Project steps:

1. Establish priority for scheduled orders.
	1. Create query to pull order schedule dates.
	2. Create a priority list based on those dates.
2. Create the schedule based on priority list.
	1. 