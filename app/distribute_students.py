from util.file import read_from_csv
from datetime import datetime
from util import get_canvas_instance
import logging
import sys
import traceback
import random
import collections
import os

canvas = None

def distribute_students(parent_course_id, child_course_ids, student_limit):

    _child_course_index = 0

    # scan each child course for duplicate enrollments (multiple sections) and cleanup
    for child_course_id in child_course_ids:
        if not de_dup_students(child_course_id):
            logging.error("Problem scanning child course {} for duplication".format(child_course_id))
            return False

    break_out = False
    while _child_course_index < len(child_course_ids):

        # Get students from parent, as a list of user_ids
        student_list = get_students(parent_course_id)

        if not student_list:
            logging.info("No students found to distribute.")
            return True        
        logging.info("{} students found to distribute.".format(len(student_list)))

        # if student already in one of the child courses, unenroll parent and pop the student from the student_list
        dup_user_id_in_child_courses = students_in_courses(child_course_ids, list(student_list.keys()))
        if dup_user_id_in_child_courses == False:
            logging.info("Problem checking duplicate registration")
            return False
        for dup_user_id in dup_user_id_in_child_courses:
            logging.info("Student user_id:{} - already in one of the child courses.  Unenroll from parent {} and skip".format(dup_user_id, parent_course_id))
            enrollment = unenroll_user(parent_course_id, student_list[dup_user_id])
            if not enrollment:
                logging.warning("Could not unenroll user from course.")
                return False
            student_list.pop(dup_user_id, None)

        # randomize list
        items = list(student_list.items())
        random.shuffle(items)
        student_list = collections.OrderedDict(items)

        child_course_id = child_course_ids[_child_course_index]

        # Get sections from child course, as a OrderedDict with section_id as key user_count as value
        sections = get_sections(child_course_id)
        if not sections:
            logging.debug("course_id:{} - No sections found.".format(child_course_id))
            _child_course_index += 1
            continue

        # Distribute each student
        for student_id in student_list:

            # Remove any sections with >LIMIT enrollment
            delete = [section for section in sections if sections[section]['count'] >= student_limit]
            for section in delete: del sections[section]

            # Remove any section that doesn't have a group_id associated with it
            delete = [section for section in sections if 'group_id' not in sections[section]]
            for section in delete: del sections[section]

            # check if any sections remain
            if not sections:
                logging.debug("course_id:{} - All sections full.".format(child_course_id))
                _child_course_index += 1
                break_out = True
                break

            # sort section list. fill up section by section
            sections = collections.OrderedDict(sorted(sections.items(), key=lambda t: -t[1]['count']))

            target_section = next(iter(sections))

            group_id = sections[target_section]['group_id']

            # Enroll user in least populated section
            logging.info("Distributing user_id:{} into section_id:{}".format(student_id, target_section))
            enrollment = enroll_user(student_id, target_section, group_id)
            if not enrollment:
                logging.warning("Could not enroll user in section.")
                return False
            sections[target_section] += 1

            # Unenroll user from parent course
            enrollment = unenroll_user(parent_course_id, student_list[student_id])
            if not enrollment:
                logging.warning("Could not unenroll user from course.")
                return False
        if break_out:
            continue
        return True

    logging.warning("All sections full. Halting student distribution.")
    return False


def get_students(course_id):
    logging.debug("Getting students for course_id:{}".format(course_id))
    students = canvas.call_api("courses/{course_id}/enrollments".format(course_id=course_id),
                               post_fields={"type":"StudentEnrollment"})
    if 'message' in students:
        logging.warning(students['message'])
        return False
    if 'errors' in students:
        for error in students['errors']:
            logging.error(error['message'])
        return False


    # convert to OrderedDict w/ user_id as key & enrollment_id as value
    return_dict = collections.OrderedDict([(student['user_id'], student['id']) for student in students])
    return return_dict


def get_sections(course_id):
    logging.debug("Getting sections for course_id:{}".format(course_id))
    sections = canvas.call_api("courses/{course_id}/sections".format(course_id=course_id),
                               post_fields={"include":"students"})
    if 'message' in sections:
        logging.warning(sections['message'])
        return False
    if 'errors' in sections:
        for error in sections['errors']:
            logging.error(error['message'])
        return False

    # convert to dict w/ section_id as key & student_count as value
    return_dict = collections.OrderedDict([(section['id'], {"name": section['name'], "count":len(section['students']) if section['students'] else 0}) for section in sections])

    # get all the groups in the course
    groups = canvas.call_api("courses/{course_id}/groups".format(course_id=course_id))
    if 'message' in groups:
        logging.warning(groups['message'])
        return False
    if 'errors' in groups:
        for error in groups['errors']:
            logging.error(error['message'])
        return False

    # assign a group_id if the last two characters matches the last two characters of the section name
    for section in return_dict:
        for group in groups:
            if return_dict[section]['name'][-2:] == group['name'][-2:]:
                return_dict[section]['group_id'] = group['id']
                break
    
    return return_dict


def enroll_user(user_id, section_id, group_id=None):
    logging.debug("Enrolling user_id:{user_id} in section_id:{section_id}".format(user_id=user_id,section_id=section_id))
    enrollment = canvas.call_api("sections/{section_id}/enrollments".format(section_id=section_id),
                                 method="POST",
                                 post_fields={"enrollment[user_id]":user_id,
                                              "enrollment[enrollment_state]":"active"})
    if 'message' in enrollment:
        logging.warning(enrollment['message'])
        return False
    if 'errors' in enrollment:
        for error in enrollment['errors']:
            logging.error(error['message'])
        return False

    # add user to group if given
    if group_id:
        group_membership= canvas.call_api("groups/{}/memberships".format(group_id),
                                          method="POST",
                                          post_fields={"user_id":user_id})

    return enrollment

def unenroll_user(course_id, enrollment_id):
    logging.debug("Unenrolling enrollment_id:{enrollment_id} from course_id:{course_id}".format(enrollment_id=enrollment_id, course_id=course_id))
    enrollment = canvas.call_api("courses/{course_id}/enrollments/{enrollment_id}".format(course_id=course_id,enrollment_id=enrollment_id),
                                 method="DELETE",
                                 post_fields={"task":"delete"})
    if 'message' in enrollment:
        logging.warning(enrollment['message'])
        return False
    if 'errors' in enrollment:
        for error in enrollment['errors']:
            logging.error(error['message'])
        return False

    return enrollment

def students_in_courses(course_ids, student_user_ids):
    """ Return a set of user id for those given user id registered as students in any given courses """
    result = set()
    for course_id in course_ids:
        course_student_list = get_students(course_id)

        if course_student_list == False:
            return False

        for user_id in student_user_ids:
            if user_id in course_student_list:
                result.add(user_id)
    return result

def de_dup_students(course_id):
    """ Remove duplicate enrollments within a course """
    students = canvas.call_api("courses/{course_id}/enrollments".format(course_id=course_id),
                               post_fields={"type":"StudentEnrollment"})
    if 'message' in students:
        logging.warning(students['message'])
        return False
    if 'errors' in students:
        for error in students['errors']:
            logging.error(error['message'])
        return False

    # create a dict with user_id as key and list of enrollment_id as value
    students = [(student['user_id'], student['id']) for student in students]
    enrollment_in_course = collections.defaultdict(list)
    for user_id, enrollment_id in students:
        enrollment_in_course[user_id].append(enrollment_id)

    for user_id in enrollment_in_course:
        if len(enrollment_in_course.get(user_id)) > 1:
            logging.info("Student user_id: {} enrolled in multiple sections of course {}. Remove all but one".format(user_id, course_id))
            for enrollment_id in enrollment_in_course.get(user_id)[1:]:
                if unenroll_user(course_id, enrollment_id) == False:
                    logging.error("Problem unenrolling uer_id:{} with enrollment id {}".format(user_id, enrollment_id))
                    return False

    return True

if __name__ == "__main__":
    # Get Input
    try:
        logging.debug("Getting input")
        if len(sys.argv) > 1:
            logging.info("Reading from file {}".format(sys.argv[1]))
            _input = read_from_csv(sys.argv[1])
        elif not sys.stdin.isatty():
            logging.info("Reading from stdin...")
            _input = read_stdin_as_csv(sys.stdin)
        else:
            logging.warning("No input given")
            sys.exit(1)
    except Exception as e:
        traceback.print_exc()
        logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
        logging.warning("Could not get input")
        sys.exit(1)

    # Get Canvas instance
    try:
        logging.debug("Getting Canvas instance")
        canvas = get_canvas_instance()
    except Exception as e:
        traceback.print_exc()
        logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
        logging.warning("Could not get Canvas instance")
        sys.exit(1)

    # Process input
    if _input:
        for row in _input:
            try:
                parent_course_id = row[0]
                child_course_ids = row[1].split(",")
                student_limit = row[2]
                logging.info("(parent:'{}', children:'{}', student_limit:'{}') started".format(parent_course_id, child_course_ids, student_limit))
                distribute_students(parent_course_id, child_course_ids, student_limit)
            except Exception as e:
                traceback.print_exc()
                logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
            finally:
                logging.info("(parent:'{}', children:'{}', student_limit:'{}') complete".format(parent_course_id, child_course_ids, student_limit))
    logging.info("Distribution completed.")

