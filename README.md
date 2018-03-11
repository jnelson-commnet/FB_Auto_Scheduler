# FB_Auto_Scheduler

The goal of this project is to create an quick method of rescheduling production around variable requirements.  The earlier stages will use priority data to create an idealized schedule for the user.  That will expand to consider labor and inventory availability.  The next step will be comparing the newly created schedule to the one in FB.  That will then produce a list of changes necessary for the user to execute.  If possible, the final planned iteration would also execute the changes without user intervention.


Project steps:

1. Establish priority for scheduled orders.
	1. (Done) Create query to pull order schedule dates.
	2. (Done) Create a priority list based on those dates.
	3. Switch from assigning priority by date to a different source (TBD).
2. Create the schedule based on priority list.
	1. (Done) Use labor data to assign an ideal schedule based on MO priority.
3. Run a resulting schedule through FB_Sim.
	1. (Done) Use the output schedule to adjust FB order data.
	2. (Done) Run orders through FB_Sim.
4. Analyze shortages.
	1. (Done) Check the resulting order timeline for purchased material shortages.
	2. (Done) Analyze the lead times of those shortages to find orders requiring rescheduling.
	3. Add logic to account for existing orders or look for ways to bring scheduling of priority orders in.
5. Create loop to repeat steps 2 thru 4.
	1. (Done) Create a loop that will create a schedule, run it, and check for issues.  It should continue looping until no schedule problems are remaining.
6. Add differentiation for labor type.
	1. Split the existing scheduling method to schedule work by mfg center.
7. Add analysis of and rescheduling for internal production shortages.
	1. Start considering parts made in house for shortage timing as well.
	2. Use the findings to reschedule mfg centers.
8. Use sales priority.
	1. Create method of retrieving SO priority and labor data.
	2. Use that data to reschedule work and purchases for sales targets.