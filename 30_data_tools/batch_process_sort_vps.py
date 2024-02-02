from move_vps_to_sort import main as move_vps_to_sort
from sort_input_files import main as sort_input_files
from add_data_to_db import main as add_data_to_db

def main():
    move_vps_to_sort()
    print("files moved to to_sort")

    sort_input_files()
    print("input files sorted")

    add_data_to_db
    print("db upated")


if __name__ == '__main__':
    main()