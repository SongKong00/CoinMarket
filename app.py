from bson import ObjectId
from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient

client = MongoClient("mongodb+srv://hesong1:thdgkdms1!@song.h22vyph.mongodb.net/?retryWrites=true&w=majority")
db = client["software_engineering"]

# JWT 토큰을 만들 때 필요한 비밀문자열입니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'HAEUN'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

import hashlib


#################################
##      HTML을 주는 부분        ##
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

        #전체 글 목록 조회 
        posting = db.post.find()

        # history 조회
        data = db.market.find_one({}, {'history': 1})
        history = data['history']

        return render_template('mypage.html', nickname=user_info["nick"], money=user_info["money"], coinNum=user_info["coinNum"], posts = posts, user_id = user_id, posting=posting, history=history)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    market_info = db.market.find_one({"_id": ObjectId('6469a502214a03383c08f340')})
    return render_template('login.html', msg=msg)


@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/main')
def main():
    #경로문제???
     # history 조회
    #data = db.market.find_one({}, {'history': 1})
    #history = data['history']

    data = db.market.find_one({}, {'history': 1}) 
    history = data['history']

    dates = [item['date'] for item in history]
    prices = [item['price'] for item in history]

    market_info = db.market.find_one({"_id": ObjectId('6469a502214a03383c08f340')})

    return render_template('main.html', currentPrice = market_info["currentPrice"], dates=dates, prices=prices)

@app.route('/mypage')
def mypage():
    return render_template('mypage.html')

@app.route('/transaction')
def transaction():
    return render_template('transaction.html')

@app.route('/add')
def add():
    return render_template('add.html')

@app.route('/withdraw')
def withdraw():
    return render_template('withdraw.html')

@app.route('/usersell')
def usersell():
    return render_template('usersell.html')

@app.route('/market')
def market():
    market_info = db.market.find_one({"_id": ObjectId('6469a502214a03383c08f340')})
    return render_template('market.html', remainCoin = market_info["remainCoin"], currentPrice = market_info["currentPrice"])

@app.route('/all_post')
def posts():
    return render_template('all_post.html')


#################################
##      로그인을 위한 API       ##
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



#[입금 API]
@app.route('/api/addmoney', methods=['POST'])
def api_addmoney():
    token_receive = request.cookies.get('mytoken')
    money_receive = request.form['money_give']

    try:
        #토큰으로 회원확인
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        #입금액 db 저장
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
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})

        #출금액이 잔액보다 많은 경우
        if (userinfo['money'] < int(withdraw_money_receive)):
            return jsonify({'result': 'fail', 'msg': '출금할 금액이 잔액을 초과하였습니다.'})
        #출금액 db 저장
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

    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    print(payload)

    userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})

    if (userinfo['coinNum'] < int(sell_coin_receive)):
        return jsonify({'result': 'fail', 'msg': '판매할 코인 개수가 보유한 코인 개수를 초과하였습니다.'})
    else:
        post = {'sellCoin': int(sell_coin_receive), 'price': int(sell_price_receive), 'done': False, 'id': payload['id']}
        post_id = db.post.insert_one(post).inserted_id
        db.user.update_one({'id': payload['id']}, {'$push': {'post': post_id}})
        return jsonify({'result': 'success'})



#[사용자 글 내역 조회]
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


#[전체 판매 글 내역 조회]
@app.route('/posts', methods=['GET'])
def get_posts():
    token_receive = request.cookies.get('mytoken')
    
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # 글(collection) 조회
    posting = db.post.find()
    
    return render_template('all_post.html', posting = posting)


#[전체 판매 글 내역 코인개수 기준 필터]
@app.route('/posts/sellCoin', methods=['GET'])
def get_posts_sellcoin():
    token_receive = request.cookies.get('mytoken')
    
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # 글(collection) 코인 개수 오름차순 조회
    posting = db.post.find().sort("sellCoin", 1)
    
    return render_template('all_post.html', posting = posting)


#[전체 판매 글 내역 코인가격 기준 필터]
@app.route('/posts/price', methods=['GET'])
def get_posts_price():
    token_receive = request.cookies.get('mytoken')
    
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # 글(collection) 코인 가격 오름차순 조회
    posting = db.post.find().sort("price", 1)
    
    return render_template('all_post.html', posting = posting)


#[코인 가격 변동 추이 조회]
@app.route('/history', methods=['GET'])
def get_history():
    token_receive = request.cookies.get('mytoken')
    
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

    # history 조회
    data = db.market.find_one({}, {'history': 1})
    history = data['history']

    dates = [item['date'] for item in history]
    prices = [item['price'] for item in history]

    return render_template('main.html', history=history)


    
#[마켓에서 코인 구매]
@app.route('/market', methods=['POST'])
def buy_coins():
    token_receive = request.cookies.get('mytoken')
    market_coin_receive = request.form['market_coin_give']

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        marketinfo = db.market.find_one({"_id": ObjectId('6469a502214a03383c08f340')})

        if (marketinfo['remainCoin'] < int(market_coin_receive)):
            return jsonify({'result': 'fail', 'msg': '구매할 코인 개수가 마켓의 잔여 코인 개수를 초과하였습니다.'})
        elif (userinfo['money'] < (int(market_coin_receive)*marketinfo['currentPrice'])):
            return jsonify({'result': 'fail', 'msg': '잔액이 부족합니다.'})
        else:
            # 마켓 코인 개수, 유저 코인 개수, 잔액 update
            db.market.update_one({"remainCoin": marketinfo['remainCoin']}, {"$set": {"remainCoin": marketinfo['remainCoin'] - int(market_coin_receive)}})
            db.user.update_one({"coinNum": userinfo['coinNum']}, {"$set": {"coinNum": userinfo['coinNum'] + int(market_coin_receive)}})
            db.user.update_one({"money": userinfo['money']}, {"$set": {"money": userinfo['money'] - (int(market_coin_receive)*marketinfo['currentPrice'])}})

            return jsonify({'result': 'success', 'remainCoin': marketinfo['remainCoin']})
            
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})



#[유저로부터 코인 구매]
@app.route('/user/<post_id>/buy', methods=['POST'])
def buy_user_coins(post_id):
    token_receive = request.cookies.get('mytoken')
    done_receive = request.form['buy_give']
    current_time = datetime.datetime.now()

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        postinfo = db.post.find_one({'_id': ObjectId(post_id)})
        marketinfo = db.market.find_one({"_id": ObjectId('6469a502214a03383c08f340')})
        selluserinfo = db.user.find_one({'post': {'$elemMatch': {'$eq': ObjectId(postinfo['_id'])}}})

        if (postinfo['done'] == True):
            return jsonify({'result': 'fail', 'msg': '이미 판매가 완료되었습니다.'})
        elif (userinfo['money'] < (int(postinfo['sellCoin'])*int(postinfo['price']))):
            return jsonify({'result': 'fail', 'msg': '잔액이 부족합니다.'})
        else:
            history_item = {'price': int(postinfo['price']), 'date': str(current_time.date())}
            #판매자/구매자 코인 개수/잔액, 마켓 코인 가격/히스토리, 글 update
            db.user.update_one({"coinNum": userinfo['coinNum']}, {"$set": {"coinNum": (userinfo['coinNum'] + int(postinfo['sellCoin']))}})
            db.user.update_one({"money": userinfo['money']}, {"$set": {"money": userinfo['money'] - (int(postinfo['sellCoin'])*int(postinfo['price']))}})
            db.user.update_one({"money": selluserinfo['money']}, {"$set": {"money": selluserinfo['money'] + (int(postinfo['sellCoin'])*int(postinfo['price']))}})
            db.user.update_one({"coinNum": selluserinfo['coinNum']}, {"$set": {"coinNum": selluserinfo['coinNum'] - int(postinfo['sellCoin'])}})
            db.user.update_one({}, {"$pull": {"post": {"_id": ObjectId(postinfo['_id'])}}})
            db.post.update_one({"done": postinfo['done']}, {"$set": {"done": True}})
            db.post.delete_one({"_id": ObjectId(postinfo['_id'])})
            db.market.update_one({"currentPrice":marketinfo['currentPrice']},  {"$set": {"currentPrice": int(postinfo['price'])}})
            db.market.update_one({'_id': marketinfo["_id"]}, {'$addToSet': {'history': history_item}})

            return jsonify({'result': 'success'})
            
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})
      

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
    
#[로그인 여부 확인]
#@app.route('/user/<user_id>/posts', methods=['GET'])
#def profile():
#    token_receive = request.cookies.get('mytoken')#토큰을 가져옴

#    if token_receive:
        # 토큰 유효성 검사 로직
        # 유효한 토큰인지 확인하고 사용자 정보를 반환
        # 사용자(collection) 조회
#        user = db.user.find_one({'_id': ObjectId(user_id)})
#        user_id = str(user['_id'])
#        return jsonify({'user_id': '유저 아이디입니다'})
#    else:
#        return jsonify({'message': '로그인이 필요합니다.'})

