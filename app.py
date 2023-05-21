from bson import ObjectId
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient

client = MongoClient("mongodb+srv://hesong1:thdgkdms1!@song.h22vyph.mongodb.net/?retryWrites=true&w=majority")
db = client["software_engineering"]

# JWT 토큰을 만들 때 필요한 비밀문자열입니다. 아무거나 입력해도 괜찮습니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'HAEUN'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib


#################################
##  HTML을 주는 부분             ##
#################################
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        
        user_id = str(user_info['_id'])
        
        # 사용자가 작성한 글 목록 조회
        post_ids = user_info['post']
        posts = db.post.find({'_id': {'$in': post_ids}})

        return render_template('index.html', nickname=user_info["nick"], money=user_info["money"], coinNum=user_info["coinNum"], posts = posts, user_id = user_id)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/add')
def add():
    return render_template('add.html')

@app.route('/withdraw')
def withdraw():
    return render_template('withdraw.html')

@app.route('/usersell')
def usersell():
    return render_template('usersell.html')



#################################
##  로그인을 위한 API            ##
#################################

# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/api/register', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive, 'coinNum': 0, 'money': 0, 'post':[]}).inserted_id

    return jsonify({'result': 'success'})


# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
# @app.route('/api/nick', methods=['GET'])
# def api_valid():
#     token_receive = request.cookies.get('mytoken')

#     # try / catch 문?
#     # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

#     try:
#         # token을 시크릿키로 디코딩합니다.
#         # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#         print(payload)

#         # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
#         # 여기에선 그 예로 닉네임을 보내주겠습니다.
#         userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
#         return jsonify({'result': 'success', 'nickname': userinfo['nick'], 'money': userinfo['money'], 'coinNum': userinfo['coinNum']})
#     except jwt.ExpiredSignatureError:
#         # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
#         return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
#     except jwt.exceptions.DecodeError:
#         return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

#[입금 API]
@app.route('/api/addmoney', methods=['POST'])
def api_addmoney():
    token_receive = request.cookies.get('mytoken')
    money_receive = request.form['money_give']

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        db.user.update_one({"money": userinfo['money']}, {"$set": {"money": userinfo['money']+int(money_receive)}})
        return jsonify({'result': 'success', 'money': userinfo['money']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})
    

#[출금 API]
@app.route('/api/withdrawmoney', methods=['POST'])
def api_withdrawmoney():
    token_receive = request.cookies.get('mytoken')
    withdraw_money_receive = request.form['withdraw_money_give']

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        if (userinfo['money'] < int(withdraw_money_receive)):
            return jsonify({'result': 'fail', 'msg': '출금할 금액이 잔액을 초과하였습니다.'})
        else:
            db.user.update_one({"money": userinfo['money']}, {"$set": {"money": userinfo['money']-int(withdraw_money_receive)}})
            return jsonify({'result': 'success', 'money': userinfo['money']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})



#[사용자 판매 글 작성 API]
@app.route('/api/usersell', methods=['POST'])
def api_usersell():
    token_receive = request.cookies.get('mytoken')
    sell_coin_receive = request.form['sell_coin_give']
    sell_price_receive = request.form['sell_price_give']

    
    # token을 시크릿키로 디코딩합니다.
    # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    print(payload)

    # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
    # 여기에선 그 예로 닉네임을 보내주겠습니다.
    post = {'sellCoin': sell_coin_receive, 'price': sell_price_receive, 'id': payload['id']}
    post_id = db.post.insert_one(post).inserted_id
    

    db.user.update_one({'id': payload['id']}, {'$push': {'post': post_id}})

    return jsonify({'result': 'success'})



# @app.route('/api/user', methods=['GET'])
# def user_posts(id):

#     token_receive = request.cookies.get('mytoken')
    
#     payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#     print(payload)

#     # 사용자(collection) 조회
#     user = db.user.find_one({'_id': ObjectId(id)})
#     user_id = str(user["_id"])

#     return jsonify(result='success', user_id=user_id)



@app.route('/user/<user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    token_receive = request.cookies.get('mytoken')
    
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # 사용자(collection) 조회
    user = db.user.find_one({'_id': ObjectId(user_id)})
    user_id = str(user['_id'])
    print(user_id)

    # 사용자가 작성한 글 목록 조회
    post_ids = user['post']  # 사용자 문서의 'posts' 필드에서 글 ID 목록 가져오기
    posts = db.post.find({'_id': {'$in': post_ids}})  # 글 ID 목록을 사용하여 'posts' collection에서 글 조회

    return render_template('user_post.html', posts = posts)


      

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)

