from app import create_app
if __name__ == '__main__':
    from waitress import serve
    serve(create_app(),host='127.0.0.1',port=5055,threads=4)
