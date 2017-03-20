"""Reference - https://github.com/jayelm/decisiontrees"""

import csv
from collections import Counter
import math
import sys




log = open("Rules.txt","w")
sys.stdout = log

class DTree(object):

    def __init__(self, training_file):
        self.training_file = training_file
        self.root = None
        self.parse_csv()
        self.get_distinct_values()

    def parse_csv(self, dependent_index=-1):

        if dependent_index != -1:
            raise NotImplementedError

        reader = csv.reader(self.training_file,delimiter=' ')
        attributes = reader.next()
        data = []
        for row in reader:
            row = dict(zip(attributes, row))
            data.append(row)
        self.training_file.close()

        self.dependent = attributes[dependent_index]
        self.attributes = [a for a in attributes if a != self.dependent]
        self.all_attributes = attributes
        self.data = data

    def get_distinct_values(self):

        values = {}
        for attr in self.all_attributes:  # Use all attributes because ugly
            values[attr] = set(r[attr] for r in self.data)
        self.values = values

    def plot(self, x=1, y=1):

        self.root._plot()

    def decide(self, attributes):

        if len(attributes) != len(self.attribute_order):
            print self.attribute_order
            raise ValueError("supplied attributes do not match data")
        attrs_dict = dict(zip(self.attribute_order, attributes))
        return self.root._decide(attrs_dict)
		
    def filter_subset(self, subset, attr, value):

        return [r for r in subset if r[attr] == value]

    def value_counts(self, subset, attr, value, base=False):

        counts = Counter()
        for row in subset:
            if row[attr] == value or base:
                counts[row[self.dependent]] += 1
        return counts

    def rules(self):

        return sorted(
            self.root._rules(),
            key=lambda t: (len(t), [p[1] for p in t if isinstance(p, tuple)])
        )

    def set_attributes(self, attributes):

        self.attribute_order = attributes

    def attr_counts(self, subset, attr):

        counts = Counter()
        for row in subset:
            counts[row[attr]] += 1
        return counts

    
    def depth(self):

        return self.root._depth(0)

    def num_leaves(self):

        if self.root.leaf:
            return 1
        else:
            return sum(c._num_leaves for c in self.root.children)

    def distinct_values(self):

        values_list = []
        for s in self.values.values():
            for val in s:
                values_list.append(val)
        return values_list

    def __str__(self):

        return "decision tree for {0}:\nDependent variable: {1}\n{2}".format(
            self.training_file.name,
            self.dependent,
            self.root
        )

    def __repr__(self):

        return ("decision tree for {0}:\nDependent variable: {1}\n{2}\n" +
                "Rows: {3}\nValues: {4}\nBase Data Entropy: {5}").format(
            self.training_file.name,
            self.dependent,
            repr(self.root),
            len(self.data),
            self.values,
            self.get_base_entropy(self.data)
        )

    def decision_repl(self):

        print
        print ','.join("{{{0}}}".format(a) for a in self.attributes)
        print "Decision tree REPL. Enter above parameters separated by commas,"
        print "no spaces between commas or brackets."
        while True:
            x = raw_input('> ').split(',')
            print "{0} ->".format(x)
            try:
                print self.decide(x)
            except Exception as e:
                print "Error with decision: {0}".format(e)


class DTreeNode(object):

    def __init__(self, label, parent_value=None, properties={}, leaf=False):

        self.label = label
        self.children = []
        self.parent_value = parent_value
        self.properties = properties
        self.leaf = leaf

    def _plot(self, xoffset, yoffset):

        raise NotImplementedError

    def _decide(self, attrs_dict):

        if self.leaf:
            return self.label
        val = attrs_dict[self.label]
        for node in self.children:
            if val == node.parent_value:
                return node._decide(attrs_dict)
        raise ValueError("Invalid property found: {0}".format(val))

    def add_child(self, node):

        self.children.append(node)

    def num_children(self):

        return len(self.children)

    def _num_leaves(self):

        if self.leaf:
            return 1
        else:
            return sum(c.num_leaves for c in self.children)

    def _depth(self, init):

        if self.leaf:
            return init
        else:
            return max(c._depth(init+1) for c in self.children)

    def _rules(self, parent=None, previous=()):

        # import pdb; pdb.set_trace()
        rows = []
        if parent is not None:
            previous += ((parent.label, self.parent_value), )
        if self.leaf:
            previous += ((self.label), )
            rows.append(previous)
        else:
            for node in self.children:
                rows.extend(node._rules(self, previous))
        return rows

    def __str__(self):

        return "--{0}--({1}, {2})".format(
            self.parent_value,
            self.label,
            ', '.join(str(c) for c in self.children)
        )

    def __repr__(self):

        return "--{0}--({1} {2}, {3})".format(
            self.parent_value,
            self.label,
            self.properties,
            ', '.join(repr(c) for c in self.children)
        )

class ID3(DTree):

    def create_tree(self, parent_subset=None, parent=None, parent_value=None,
                    remaining=None):

        if parent_subset is None:
            subset = self.data
        else:
            subset = self.filter_subset(parent_subset,
                                        parent.label,
                                        parent_value)

        if remaining is None:
            remaining = self.attributes

        use_parent = False
        counts = self.attr_counts(subset, self.dependent)
        if not counts:

            subset = parent_subset
            counts = self.attr_counts(subset, self.dependent)
            use_parent = True

        if len(counts) == 1: 
            node = DTreeNode(
                label=counts.keys()[0],
                leaf=True,
                parent_value=parent_value
            )
        elif not remaining or use_parent:

            most_common = max(counts, key=lambda k: counts[k])
            node = DTreeNode(
                label=most_common,
                leaf=True,
                parent_value=parent_value,
                properties={'estimated': True}
            )
        else:

            igains = []
            for attr in remaining:
                igains.append((attr, self.information_gain(subset, attr)))

            max_attr = max(igains, key=lambda a: a[1])

            node = DTreeNode(
                max_attr[0],
                properties={'information_gain': max_attr[1]},
                parent_value=parent_value
            )

        if parent is None:
            self.set_attributes(self.attributes)
            self.root = node
        else:
            parent.add_child(node)

        if not node.leaf:  
            new_remaining = remaining[:]
            new_remaining.remove(node.label)
            for value in self.values[node.label]:
                self.create_tree(
                    parent_subset=subset,
                    parent=node,
                    parent_value=value,
                    remaining=new_remaining
                )

    def information_gain(self, subset, attr):
        
        gain = self.get_base_entropy(subset)
        counts = self.attr_counts(subset, attr)
        total = float(sum(counts.values()))  # Coerce to float for division
        for value in self.values[attr]:
            gain += -((counts[value]/total)*self.entropy(subset, attr, value))
        return gain

    def get_base_entropy(self, subset):
        
        return self.entropy(subset, self.dependent, None, base=True)

    def entropy(self, subset, attr, value, base=False):
        
        counts = self.value_counts(subset, attr, value, base)
        total = float(sum(counts.values())) 
        entropy = 0
        for dv in counts: 
            proportion = counts[dv] / total
            entropy += -(proportion*math.log(proportion, 2))
        return entropy


if __name__ == '__main__':
    import argparse
    import pprint
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('training_file', type=argparse.FileType('r'),
                        help='name of the (training) .csv file')
    parser.add_argument('-d', '--decide', action='store_true',
                        help='enter decision REPL for the given tree')
    parser.add_argument('-r', '--rules', action='store_true',
                        help='print out individual paths down the tree for'
                        'binary decisions') 

    args = parser.parse_args()
    

    id3 = ID3(args.training_file)
    id3.create_tree()
    print repr(id3)

    if args.rules:
        pprint.pprint(id3.rules(), width=400)


    if args.decide:
        id3.decision_repl()

		
