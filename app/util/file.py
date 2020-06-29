import logging
import csv, sys, os
import traceback

def read_from_csv(csv_file, data_has_headers=False, fieldnames=None):
    '''Turns a CSV file into a list.'''
    csv_file = csv_file.replace('"', '')
    try:
        return_list = []
        with open(csv_file) as csvfile:
            if data_has_headers:
                reader = csv.DictReader(csvfile)
            elif fieldnames:
                reader = csv.DictReader(csvfile, fieldnames=fieldnames)
            else:
                reader = csv.reader(csvfile)
            for row in reader:
                return_list.append(row)
            return return_list
    except IOError as e:
        print("I/O error({0} : {1})".format(e.errno, e))
    except UnicodeDecodeError as e:
        print("UnicodeDecodeError: {0}".format(e))
    finally:
        return return_list
    

def write_to_csv(filename, content, fieldnames=None, path="output"):
    '''Turns a list into a CSV file.'''
    keep_trying = True
    while keep_trying:
        logging.info("writing content to file '{filename}'...".format(filename=filename))
        try:
            if not os.path.exists(path):
                os.makedirs(path)
            with open(path+"/"+filename, 'w', newline='') as csvfile:
                if fieldnames:
                    writer = csv.DictWriter(csvfile,fieldnames=fieldnames)
                    writer.writeheader()
                else:
                    writer = csv.writer(csvfile)
                    
                for row in content:
                    writer.writerow(row)
            logging.info("completed writing content to file.")
            keep_trying = False
        except Exception as e:
            traceback.print_exc()
            logging.error("could not write content to file: {}".format(e))
            if input("try again? (y/n): ") != "y":
                keep_trying = False

def get_input_data(input_headers=None, url=None):
    if input_headers:
        data_has_headers = False
    else:
        data_has_headers = True
        if url:
            input_headers = [t[1] for t in string.Formatter().parse(url) if t[1] is not None]

    if len(sys.argv) > 1:
        if len(sys.argv) > 1:
            return read_from_csv(sys.argv[1], data_has_headers=data_has_headers, fieldnames=input_headers)
    elif input_headers:
        return [{header:input("{}: ".format(header)) for header in input_headers}]
    else:
        return [{}]

