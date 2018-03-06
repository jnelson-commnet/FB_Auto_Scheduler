__Author__ = 'Jack'

import query module
import auto scheduler
import fb sim

# Get all info needed from FB:

run_queries()

# Start by using the basic auto scheduler to make an "ideal schedule."  This would be for a base planning production area.
# 	So we'll begin with Pro Line.

idealSchedule = run_auto_schedule(proLine, moPriority, moLaborNeeded, laborAvailable) 	# Auto schedule should need to know the production area
																						# as well as the labor available, labor needed, and MO
																						# priority.

# The resulting schedule assumes everything is ready for the Pro Line and it can process MOs by priority.  If there are part
# 	shortages, then the Pro Line will not be able to follow this schedule.  To find these part shortages, we need to run
#	the FB_Simulator.

orderTimeline = run_fb_sim(idealSchedule)	# The FB_Sim would usually run its own set of queries for everything it needs.  This should be done already
											# since a lot of this info is going to be used repeatedly.

# The order timeline will contain any phantom POs created to fill shortages in the schedule.  These shortages need to be checked for lead times.
#	If a part has a 4 week lead time, then the MO that requires the part should not be built until 4 weeks from the day the order is placed.  Assume
#	the order will be placed tomorrow and will need a day to process once received.  Plus the schedule dates are when the MOs are being finished.
#	So the "earliest end date" for each MO will be the lead time of its longest lead shortage plus 2 days for processing and the expected run time
#	of the part in the Pro Line.

updatedSchedule = analyzeTimeline(orderTimeline) # This will also need to reference labor needed/available to come up with the new finishing dates.

# Run the suto scheduler again.  It doesn't need to change the MO priority, but whenever it tries to schedule an MO before its "earliest end date,"
#	the scheduler will have to move on to the next available MO on the priority list.  That way it will bump in the next highest priority MO to fill
#	the gap created by parts shortages.

# This will create more part shortages for the MO's that were bumped up.  So we'll need to analyze the timeline again.  Keep looping through this process
#	until there are no shortages with lead times too long to fulfill by the scheduled builds.

# The next operation will be to do this for other production areas, some of which will then affect the Pro Line's start date.  This is going to
#	take a long time to run.  But we can retool it later once a base is built.

