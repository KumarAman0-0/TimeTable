"""Demo college: 3 branches, 5 sections, 13 teachers, shared rooms and labs."""
from .models import *


def build_sample() -> Problem:
    branches = [
        Branch("CSE", "Computer Science & Engg.", 0, 8, lunch_slot=4),
        Branch("ECE", "Electronics & Comm. Engg.", 0, 8, lunch_slot=5),   # different lunch
        Branch("ME", "Mechanical Engg.", 0, 7, lunch_slot=4),              # earlier finish
    ]
    sections = [
        Section("CSE-A", "CSE", "CSE 3rd Yr - A", 60),
        Section("CSE-B", "CSE", "CSE 3rd Yr - B", 58),
        Section("ECE-A", "ECE", "ECE 3rd Yr - A", 55),
        Section("ECE-B", "ECE", "ECE 3rd Yr - B", 52),
        Section("ME-A", "ME", "ME 3rd Yr - A", 50),
    ]
    teachers = [
        Teacher("T1", "Dr. R. Sharma", 2, 5), Teacher("T2", "Prof. A. Verma", 2, 5),
        Teacher("T3", "Dr. S. Gupta", 2, 5), Teacher("T4", "Prof. N. Singh", 2, 5),
        Teacher("T5", "Dr. P. Mishra", 2, 5), Teacher("T6", "Prof. K. Yadav", 2, 5),
        Teacher("T7", "Dr. M. Tiwari", 2, 5, unavailable={(5, s) for s in range(8)}),  # no Saturday
        Teacher("T8", "Prof. D. Pandey", 2, 5), Teacher("T9", "Dr. V. Saxena", 2, 5),
        Teacher("T10", "Prof. L. Dubey", 1, 5), Teacher("T11", "Dr. H. Srivastava", 1, 5),
        Teacher("T12", "Prof. G. Chauhan", 1, 5), Teacher("T13", "Dr. B. Rathore", 1, 5),
    ]
    rooms = [
        Room("R101", "Room 101", "classroom", 70), Room("R102", "Room 102", "classroom", 70),
        Room("R103", "Room 103", "classroom", 65), Room("R201", "Room 201", "classroom", 60),
        Room("R202", "Room 202", "classroom", 60),
        Room("CL1", "Computer Lab 1", "computer_lab", 60),
        Room("CL2", "Computer Lab 2", "computer_lab", 60),
        Room("EL1", "Electronics Lab", "electronics_lab", 60),
        Room("WS1", "Workshop", "workshop", 60),
    ]
    courses = [
        Course("DSA", "Data Structures", "theory", 4), Course("DBMS", "DBMS", "theory", 3),
        Course("OS", "Operating Systems", "theory", 3), Course("CN", "Computer Networks", "theory", 3),
        Course("MATH", "Engg. Mathematics-III", "theory", 4),
        Course("DSA-L", "DSA Lab", "lab", 1, 2, "computer_lab"),
        Course("DBMS-L", "DBMS Lab", "lab", 1, 2, "computer_lab"),
        Course("SIG", "Signals & Systems", "theory", 4), Course("DE", "Digital Electronics", "theory", 3),
        Course("EMT", "EM Theory", "theory", 3), Course("AC", "Analog Circuits", "theory", 3),
        Course("DE-L", "Digital Electronics Lab", "lab", 1, 2, "electronics_lab"),
        Course("AC-L", "Analog Circuits Lab", "lab", 1, 2, "electronics_lab"),
        Course("THERMO", "Thermodynamics", "theory", 4), Course("FM", "Fluid Mechanics", "theory", 3),
        Course("MECH", "Engg. Mechanics", "theory", 3), Course("MFG", "Manufacturing Process", "theory", 3),
        Course("WS-L", "Workshop Practice", "lab", 1, 2, "workshop"),
    ]
    A = Assignment
    asg = []
    for sec, tmap in (("CSE-A", dict(DSA="T1", DBMS="T2", OS="T3", CN="T5", MATH="T4", **{"DSA-L": "T1", "DBMS-L": "T2"})),
                      ("CSE-B", dict(DSA="T1", DBMS="T2", OS="T3", CN="T5", MATH="T4", **{"DSA-L": "T1", "DBMS-L": "T2"}))):
        asg += [A(sec, c, t) for c, t in tmap.items()]
    for sec in ("ECE-A", "ECE-B"):
        tmap = dict(MATH="T4", SIG="T6", DE="T7", EMT="T8", AC="T9", **{"DE-L": "T7", "AC-L": "T9"})
        asg += [A(sec, c, t) for c, t in tmap.items()]
    tmap = dict(THERMO="T10", FM="T11", MATH="T4", MECH="T12", MFG="T13", **{"WS-L": "T13"})
    asg += [A("ME-A", c, t) for c, t in tmap.items()]
    return Problem(branches, sections, teachers, rooms, courses, asg)
