# Your Agent for solving Raven's Progressive Matrices. You MUST modify this file.
#
# You may also create and submit new files in addition to modifying this file.
#
# Make sure your file retains methods with the signatures:
# def __init__(self)
# def Solve(self,problem)
#
# These methods will be necessary for the project's main method to run.

# Install Pillow and uncomment this line to access image processing.
from PIL import Image
import  numpy as np
from itertools import product
import ufarray

TOLERANCE = 50

UNCHANGED_W = 0
FILLED_W = 1
ROTATE_W = 2
DELETED_W = 10
ADDED_W = 10

# Code copied from https://github.com/spwhitt/cclabel/blob/master/cclabel.py
# I altered slightly to fit problem
# I attemted creating my own component labeling, but it was taking significant amounts of time
# Algorithm obtained from "Optimizing Two-Pass Connected-Component Labeling 
# by Kesheng Wu, Ekow Otoo, and Kenji Suzuki
#
def color_shapes(image):
    output = np.zeros(image.shape)
    width, height = image.shape
 
    # Union find data structure
    uf = ufarray.UFarray()
    uf.makeLabel()
    #
    # First pass
    #
 
    # Dictionary of point:label pairs
    labels = {}
 
    for y, x in product(range(height), range(width)):
 
        # If the current pixel is 0, it's obviously not a component...
        if image[x, y] == 0:
            pass
 
        elif y > 0 and image[x, y-1] == 1:
            labels[x, y] = labels[(x, y-1)]

        elif x+1 < width and y > 0 and image[x+1, y-1] == 1:
 
            c = labels[(x+1, y-1)]
            labels[x, y] = c

            if x > 0 and image[x-1, y-1] == 1:
                a = labels[(x-1, y-1)]
                uf.union(c, a)
 
            elif x > 0 and image[x-1, y] == 1:
                d = labels[(x-1, y)]
                uf.union(c, d)

        elif x > 0 and y > 0 and image[x-1, y-1] == 1:
            labels[x, y] = labels[(x-1, y-1)]

        elif x > 0 and image[x-1, y] == 1:
            labels[x, y] = labels[(x-1, y)]
 
        else: 
            labels[x, y] = uf.makeLabel()

    uf.flatten()

    for (i, j) in labels:

        # Name of the label the current point belongs to
        label = uf.find(labels[(i, j)])

        output[i, j] = label

    return output

def to_image_array(filename):
    image = Image.open(filename).convert("L") #opens image, converts to single channel grayscale
    im_data = np.asarray(image, dtype=np.uint8).T
    binary = np.zeros(im_data.shape)
    binary[np.where(im_data <= 128)] = 1 
    binary[np.where(im_data > 128)] = 0

    return binary

# The dilate function below was altered from the blog listed below
# http://blog.ostermiller.org/dilate-and-erode
# Changed bits are left as 2 to aid in erode the image
# dilate and erode are probably not really needed, but I did not want a possible isolated pixel to become its own object
def dilate(image):
    for (i, j) in product(range(image.shape[0]), range(image.shape[1])):
        if (image[i, j] == 1):
            if (image[i-1, j] == 0):
                image[i-1, j] = 2
            if (image[i, j-1] == 0):
                image[i, j-1] = 2
            if (i+1 < image.shape[0] and image[i+1, j] == 0):
                image[i+1, j] = 2
            if (j+1 < image.shape[1] and image[i, j+1] == 0):
                image[i, j+1] = 2
    return image

def erode(image):
    tmp = np.zeros(image.shape)
    for (i, j) in product(range(image.shape[0]), range(image.shape[1])):
        if (image[i, j] == 2):
            if (image[i-1, j] == 2):
                tmp[i-1, j] = 2
            if (image[i, j-1] == 2):
                tmp[i, j-1] = 2
            if (i+1 < image.shape[0] and image[i+1, j] == 2):
                tmp[i+1, j] = 2
            if (j+1 < image.shape[1] and image[i, j+1] == 2):
                tmp[i, j+1] = 2
    output = image - tmp
    output[np.where(output == 2)] = 1
    return output

def object_unchanged(a, b):
    if abs(np.sum(a["Shape Pixels"] - b["Shape Pixels"])) < TOLERANCE:
        return True
    else:
        return False

def object_rotated(a, b):
    c = a
    for i in [90, 180, 270]:
        c["Shape Pixels"] = np.rot90(c["Shape Pixels"])
        if object_unchanged(c, b):
            return True
    return False

class Agent:
    # The default constructor for your Agent. Make sure to execute any
    # processing necessary before your Agent starts solving problems here.
    #
    # Do not add any variables to this signature; they will not be used by
    # main().
    def __init__(self):
        pass

    def create_nodes(self, figures):
        for figure_name in figures:
            this_figure = figures[figure_name]
            this_figure.frame = {}

            # Process the image for future operations
            array = to_image_array(this_figure.visualFilename)
            array = erode(dilate(array))  # morphological open to remove possible isolated pixels
            this_figure.frame["Image"] = color_shapes(array)
            this_figure.frame["Objects"] = {}

            # Seperate each shape into its own object
            for i in range(1, int(np.amax(this_figure.frame["Image"])) + 1):
                tmp = np.zeros(this_figure.frame["Image"].shape)
                # Set pixel back to 1 for future comparisons
                tmp[np.where(this_figure.frame["Image"] == i)] = 1
                if np.sum(tmp) == 0:
                    pass
                else:
                    obj = {}
                    obj["Shape Pixels"] = tmp
                    obj["Matched to"] = ""
                    obj["Transform"] = "not matched"
                    obj["Matched Weight"] = 999
                    obj["Filled"] = ""
                    this_figure.frame["Objects"]["Object " + str(i)] = obj

            # Set pixel back to 1 for future comparisons
            this_figure.frame["Image"][np.where(this_figure.frame["Image"] > 1)] = 1

    def match(self, a, b, transform, weight):
        if transform == "DELETED":
            a["Transform"] = transform
            a["Matched Weight"] = weight
        elif transform == "ADDED":
            b["Transform"] = transform
            b["Transform"] = weight
        else:
            a["Transform"] = transform
            a["Matched Weight"] = weight
            a["Matched to"] = str(b)
            b["Matched to"] = str(a)
            b["Transform"] = transform
            b["Matched Weight"] = weight

    def match_objects(self, fig_a, fig_b):
        for a, b in product(fig_a.frame["Objects"], fig_b.frame["Objects"]):
            a_object = fig_a.frame["Objects"][a]
            b_object = fig_b.frame["Objects"][b]

            if object_unchanged(a_object, b_object):
                self.match(a_object, b_object, "UNCHANGED", UNCHANGED_W)
            elif object_rotated(a_object, b_object):
                self.match(a_object, b_object, "ROTATED", ROTATED_W)
            elif len(fig_a.frame["Objects"]) > len(fig_b.frame["Objects"]):
                self.match(a_object, b_object, "DELETED", DELETED_W)
            elif len(fig_a.frame["Objects"]) < len(fig_b.frame["Objects"]):
                self.match(a_object, b_object, "ADDED", ADDED_W)
            else:
                # print("Unable to match " + str(fig_a.name) + " and " + str(fig_b.name))
                return -1

    def array_transforms(self, a, b):
        transforms = []
        for i, j in product(a, b):
            a_object = a[i]
            b_object = b[j]

            # TODO: test for the add/delete transform
            # if object was matched, then it is not an add or a delete
            if a_object["Matched to"] != "":
                transforms.append(a_object["Transform"])
            else: #if it was not matched, then add both a and b because one will be a add/delete
                transforms.append(a_object["Transform"])
                transforms.append(b_object["Transform"])

        return transforms

    def solve_two(self, problem):

        answer = -1
        confidence = 999
        # dictionary (fig 1, fig 2) = {}
        semantic_net = {}

        semantic_net["A", "B"] = []
        semantic_net["A", "C"] = []


        # Get transformation from A to B

        if self.match_objects(problem.figures["A"], problem.figures["B"]) == -1:
            print("Skipping question")
            return -1

        semantic_net["A", "B"] = self.array_transforms(problem.figures["A"].frame["Objects"], problem.figures["B"].frame["Objects"])

        # Get transformation from A to C
        if self.match_objects(problem.figures["A"], problem.figures["C"]) == -1:
            # print("Skipping questions")
            return -1

        semantic_net["A", "C"] = self.array_transforms(problem.figures["A"].frame["Objects"], problem.figures["C"].frame["Objects"])


        if self.match_objects(problem.figures["A"], problem.figures["C"]) == -1:
            return -1

        for i in range(1,7):
            if self.match_objects(problem.figures["C"], problem.figures[str(i)]) != -1:
                semantic_net["C", str(i)] = self.array_transforms(problem.figures["C"].frame["Objects"], problem.figures[str(i)].frame["Objects"])
            if  self.match_objects(problem.figures["B"], problem.figures[str(i)]) != -1:
                semantic_net["B", str(i)] = self.array_transforms(problem.figures["B"].frame["Objects"], problem.figures[str(i)].frame["Objects"])


        for fig_i, fig_j in semantic_net:
            if fig_i == "A" and (fig_j == "B" or fig_j == "C"):
                pass
            elif fig_i == "B" and fig_j == "C":
                pass
            elif semantic_net[("C", fig_j)] == semantic_net["A", "B"] and semantic_net[("A", "C")] == semantic_net["B", fig_j]:
                answer = fig_j
                confidence = 0
            elif semantic_net[("C", fig_j)] == semantic_net["A", "B"]:
                if confidence > 10:
                    answer = fig_j
                    confidence = 10
            elif semantic_net[("B", fig_j)] == semantic_net["A", "C"]:
                if confidence > 20:
                    answer = fig_j
                    confidence = 10
        # print(answer)

        return int(answer)

    def solve_three(self, problem):

        return -1

    # The primary method for solving incoming Raven's Progressive Matrices.
    # For each problem, your Agent's Solve() method will be called. At the
    # conclusion of Solve(), your Agent should return an int representing its
    # answer to the question: 1, 2, 3, 4, 5, or 6. Strings of these ints 
    # are also the Names of the individual RavensFigures, obtained through
    # RavensFigure.getName(). Return a negative number to skip a problem.
    #
    # Make sure to return your answer *as an integer* at the end of Solve().
    # Returning your answer as a string may cause your program to crash.
    def Solve(self, problem):

        print(problem.name)

        self.create_nodes(problem.figures)

        if problem.problemType == "2x2":
            answer = self.solve_two(problem)
        else:
            answer = self.solve_three(problem)

        return answer