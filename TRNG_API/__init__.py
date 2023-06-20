import sys, os
import threading
from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from TRNG_Pendel import pendelManager

# Determines if Generating Random Numbers is possible
TRNG_RUNNING = False

# App configs
app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*":{"origins":"*"}})
#app.config['CORS_HEADERS'] = 'Content-Type'

api = Api(app)
api.prefix = '/trng'

# This Endpoint returns a True Random Number generated by our chaotic pendulum.
# There are two Parameters which changes the returned value:
# 1. quantity: Number of random numbers to get (of equal bit sequence length)
# 2. numBits: Number of random bits in each bit sequence
class GetRandomNums(Resource):
    def get(self):
        global TRNG_RUNNING
        response = ''
        manager = pendelManager.GetInstance()
        # len of result array given by parameter
        quantity = request.args.get('quantity', default=-1, type=int)
        #len of the random Bits
        numBits = request.args.get('numBits', default=-1, type=int)
        
        if numBits == -1 or quantity == -1:
            response = make_response(jsonify({'description': 'input is not numeric; enter a valid number'}), 400)
            return response
        
        if(not TRNG_RUNNING):
            response = make_response(jsonify({'description': 'system not ready; try init'}), 432)
        else:
            # Call generation from pendelManager
            try:
                result = manager.generateRandomBits(quantity, numBits)
                
                data = {
                'description': 'successful operation; HEX-encoded bit arrays (with leading zeros if required)',
                'randomBits': result
                }

                response = make_response(jsonify(data), 200)
            except Exception as ex:
                response = make_response(jsonify({'description': str(ex)}), 500)
            
        return response

# This endpoint initializes the TRNG and ensures that the endpoint GetRandomNums works.
class InitRandomNums(Resource):
    def get(self):
        global TRNG_RUNNING
        response = ''
        if(TRNG_RUNNING):
            response = make_response(jsonify({'description': 'system already running'}), 409)
        else:
            try:
                manager = pendelManager.GetInstance()
                t = threading.Thread(target=manager.checkFunctionality)
                t.start()
                t.join(timeout=59)
            except Exception as ex:
                TRNG_RUNNING = False
                response = make_response(jsonify({'description': str(ex)}), 500)
                return response
		
            if(pendelManager.BsiInitTestsPassed):
                TRNG_RUNNING = True
                response = make_response(jsonify({'description': 'successful operation; random number generator is ready and random numbers can be requested'}), 200)
            elif(t.is_alive()):
                TRNG_RUNNING = False
                response = make_response(jsonify({'description': 'unable to initialize the random number generator within a timeout of 60 seconds'}), 555)
            elif(not pendelManager.BsiInitTestsPassed):
                TRNG_RUNNING = False
                response = make_response(jsonify({'description': 'functionality not given; check hardware'}), 500)

        return response

# This endpoint shuts down the TRNG
class ShutdownRandomNums(Resource):
    def get(self):
        global TRNG_RUNNING
        response = ''
        if(TRNG_RUNNING):
            TRNG_RUNNING = False
            response = make_response(jsonify({'description': 'successful operation; random number generator has been set to \'standby mode\''}), 200)
        else:
            response = make_response(jsonify({'description': 'system already in \'standby mode\''}), 409)

        return response


api.add_resource(GetRandomNums, '/randomNum/getRandom')
api.add_resource(InitRandomNums, '/randomNum/init')
api.add_resource(ShutdownRandomNums, '/randomNum/shutdown')

if __name__ == '__main__':
     app.run(host='172.16.78.60', port=5520, ssl_context=('/var/certs/cert-connect.pem', '/var/certs/cert-connect-key.pem'))