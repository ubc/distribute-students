from util.file import read_from_csv
from datetime import datetime
from util import get_canvas_instance
import logging
import sys
import traceback
import random
import collections

canvas = None

_SECTION_ENROLLMENT_LIMIT = 35


def distribute_students(parent_course_id, child_course_ids):
    
    _child_course_index = 0

    while _child_course_index < len(child_course_ids):
        break_out = False
        
        # Get students from parent, as a list of user_ids
        student_list = get_students(parent_course_id)
        logging.info("{} students found to distribute.".format(len(student_list)))
        
        if not student_list:
            return True

        # randomize list
        items = list(student_list.items())
        random.shuffle(items)
        student_list = collections.OrderedDict(items)

        
        child_course_id = child_course_ids[_child_course_index]
        
        # Get sections from child course, as a OrderedDict with section_id as key user_count as value
        sections = get_sections(child_course_id)
        if not sections:
            logging.debug("section_id:{} - No sections found.".format(child_course_id))
            _child_course_index += 1
            continue

        # Distribute each student 
        for student_id in student_list:
            
            # Remove any sections with >LIMIT enrollment        
            delete = [section for section in sections if sections[section] >= _SECTION_ENROLLMENT_LIMIT] 
            for section in delete: del sections[section]

            # check if any sections remain
            if not sections:
                logging.debug("section_id:{} - All sections full.".format(child_course_id))
                _child_course_index += 1
                break_out = True
                break
            
            # sort section list
            sections = collections.OrderedDict(sorted(sections.items(), key=lambda t: t[1]))

            emptiest_section = next(iter(sections))
            
            # Enroll user in least populated section
            logging.info("Distributing user_id:{} into section_id:{}".format(student_id, emptiest_section))
            enrollment = enroll_user(student_id, emptiest_section)
            if not enrollment:
                logging.warning("Could not enroll user in section.")
                return False
            sections[emptiest_section] += 1

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
    return_dict = collections.OrderedDict([(section['id'], len(section['students']) if section['students'] else 0) for section in sections])
    return return_dict


def enroll_user(user_id, section_id):
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
                logging.info("(parent:'{}', children:'{}') started".format(parent_course_id, child_course_ids))
                distribute_students(parent_course_id, child_course_ids)
            except Exception as e:
                traceback.print_exc()
                logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
            finally:
                logging.info("(parent:'{}', children:'{}') complete".format(parent_course_id, child_course_ids))
    logging.info("Distribution completed.")

