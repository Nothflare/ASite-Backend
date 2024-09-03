from flask import jsonify
async def get_posts(user, type):
    response = jsonify({"data":{"title": "2", "content": "4"}})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response
async def get_posts_details(id):
    return "1"
async def new_post(user):
    return "1"
async def edit_post(user):
    return "1"
async def delete_post():
    return "1"
