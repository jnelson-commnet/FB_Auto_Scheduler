__author__ = 'Chris'

import numpy as np

"""Class for indexing"""
class Index:
    count = 0
    customcount = 0

    def __init__(self):
        Index.count += 1
        Index.customcount -= 1

    def show_index(self):
        return Index.count

    def show_fake_index(self):
        return Index.customcount

"""Class for storing make parts that don't have BOMs."""
class No_BOMs:
    partlist = []

    def __init__(self):
        self.self = self

    def add_part(self, part):
        No_BOMs.partlist.append(part)

    def get_parts(self):
        # If this line errors out, it's probably because of additional
        # builds being added.  They enter this list as a pd.Series.
        # Check additional builds for typos or missing BOMs.
        noparts = np.unique(No_BOMs.partlist)
        return noparts

"""Class for storing parts with multiple BOMs."""
class Many_BOMs:
    partlist = []

    def __init__(self):
        self.self = self

    def add_part(self, part):
        Many_BOMs.partlist.append(part)

    def get_parts(self):
        manyparts = np.unique(Many_BOMs.partlist)
        return manyparts