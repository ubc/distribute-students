import util
import logging
import sys
import traceback

def test_canvas_connection():
    logging.debug("Testing Canvas connection")
    canvas = util.get_canvas_instance()
    self = canvas.call_api("users/self")
    if not self:
        return False
    if 'message' in self:
        logging.warning(course['message'])
        return False
    if 'errors' in self:
        for error in self['errors']:
            logging.error(error['message'])
        return False
    logging.debug("Canvas connection successful")
    return self


if __name__ == "__main__":
    try:
        self = test_canvas_connection()
        if self:
            logging.info("Successfully connected to Canvas")
            sys.exit()
        else:
            logging.warning("Unable to connect to Canvas")
            
    except Exception as e:
        traceback.print_exc()
        logging.error("Unexpected error occured: {}:{}".format(type(e).__name__, e))
        sys.exit(1)
