from render_screen_images import main as render_screen_images
from process_generated_images import main as process_generated_images
from move_files import move_files
from update_generic_images_db import main as update_generic_images_db

if __name__ == '__main__':
    render_screen_images()
    print("screen images rendered")
    
    process_generated_images()
    print("generated images processed")

    move_files()
    print("files moved")

    # update_generic_images_db()
    # print("images written")