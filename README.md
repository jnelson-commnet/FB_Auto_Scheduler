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
	1. (Done) Split the existing scheduling method to schedule work by mfg center.
7. Add analysis of and rescheduling for internal production shortages.
	1. Start considering parts made in house for shortage timing as well.
	2. Use the findings to reschedule mfg centers.
8. Use sales priority.
	1. Create method of retrieving SO priority and labor data.
	2. Use that data to reschedule work and purchases for sales targets.
9. Improve ability to schedule partials.
	1. Add a field to account for work complete on open orders.
10. Create a summary of the result.
	1. Produce a clear schedule by production area.
	2. Create a report to show unused labor.
	3. Use the schedule to discover bottlenecks in production.
	4. Look for POs to target for expediting.
	5. Report excess inventory purchased or built. (e.g. extra parts purchased on longer lead time for lower cost.)
	6. Create a forecasted analysis of possible cost compared to revenue possible.
	7. Add a check for unused/non-moving inventory.


Usage Notes (Oct 16, 2018):

- Manufacture Order Query is hard coded to ignore orders marked as having planning states "40-Questionable".  Priority of MO completion is determined by the planning state field.  If a planning state is not specified, it will default to "20-Planned."
- The MFG Center Query determines labor needed per unit built.  The main fields in use are "LaborPer", which references the Unit Assembly multiple field in the BOM, and "MfgCenter", which references the Production Center.  A BOM is only referenced if it is active and listed as the default BOM of a "Make" part.
- If there is no labor information available for a part, it is assumed that the labor required is 0 hours.  This is because labor estimates for finished panels are for the whole build time needed in a production area.  So sub-assembly labor needs to be ignored.  There is a list produced at the end of the script to audit which parts are missing BOMs or Labor info.
- The lead time of a part is determined by the RealLeadTime field of a part.  If that is not usable, the part will automatically use a lead time of 15.
- The Bill of Materials query retrieves all Finished Good and Raw Good lines with positive quantities.  Raw Goods are changed to negative in the script to make order processing more natural throughout.  Only active BOMs are included.
- The inventory query sums all inventory by part, so there is no differentiation for inventory split between location groups or consideration of time needed for Transfer Orders.  Currently, the location groups considered are CA LA, WA Tech Grp, TN, and SAC.  These will need to be changed to the more active locations.
- Available labor per production group is kept in a manually updated excel sheet.  This contains the names of the production areas along with an estimate of how many hours per day are available to use toward production.
- The calendar of available hours is created in the script.  It does not include weekends.  It also doesn't skip holidays, so the script will schedule work on New Year's Day.
- Inactive Parts are included in transactions since inventory can still exist and they can be on orders.
- Purchase Order lines are assumed to be received into inventory when their scheduled fulfillment dates indicate.  There is no handling for blanket orders or stock held with a vendor.
- Sales Order priority is determined first by the Priority field, second by the Desired Customer Delivery Date field, and third by Date Issued.
- Sales Order credit return lines are currently not included in the query.
- Labor Required for each Sales Order is hard coded to be 1 hour of Shipping's time.
- Manufacture Orders are considered second priority to Sales Orders.  This means that whichever SO is highest priority can increase the priority on the MO that feeds it, even if that MO is initially labeled as low priority.