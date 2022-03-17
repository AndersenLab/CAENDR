from main import generate_thumbnails

def run_test():
    data = {
        "bucket": "caendr-photos-bucket",
        "name": "tmp-mti/MTI000.jpg"
    }
    context = {}
    generate_thumbnails(data, context)

if __name__ == '__main__':
    run_test()