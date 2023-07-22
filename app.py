import json
import os
from datetime import datetime

import pandas as pd
import redis
from flask import Flask, request, jsonify

# Step 1: Set up a local Redis cache server
redis_host = 'localhost'
redis_port = 6379
redis_db = 0
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)


# Step 2: Read the Excel data and store the latest data for each device ID in Redis cache

def store_latest_data_in_redis(excel_file):
    df = pd.read_csv(excel_file)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    df = df.sort_values(by='time_stamp', ascending=False)

    for device_id, group in df.groupby('device_fk_id'):
        location_data = []
        for _, row in group.iterrows():
            location_data.append({
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'time_stamp': str(row['time_stamp'])
            })

        # Store the location data list in Redis with the device ID as the key
        redis_client.hset(device_id, 'location_data', json.dumps(location_data))

        start_location = (float(group['latitude'].iloc[-1]), float(group['longitude'].iloc[-1]))
        end_location = (float(group['latitude'].iloc[0]), float(group['longitude'].iloc[0]))

        # Convert time_stamp to string format to store in Redis (assuming you need it as a string)
        start_time_stamp = str(group['time_stamp'].iloc[-1])
        end_time_stamp = str(group['time_stamp'].iloc[0])

        # Store the start and end locations in Redis with the device ID as the key
        redis_client.hmset(device_id, {'start_latitude': start_location[0],
                                       'start_longitude': start_location[1],
                                       'end_latitude': end_location[0],
                                       'end_longitude': end_location[1],
                                       'start_time_stamp': start_time_stamp,
                                       'end_time_stamp': end_time_stamp})


# Step 3: Create API endpoints using Flask
app = Flask(__name__)


# API endpoint for retrieving device's latest information
@app.route('/api/latest_info/<int:device_id>', methods=['GET'])
def get_latest_info(device_id):
    data = redis_client.hgetall(str(device_id))
    # Convert byte strings to regular strings
    latest_info = {key.decode('utf-8'): value.decode('utf-8') for key, value in data.items()}
    latest_info.pop('location_data', None)
    return jsonify({'device_id': device_id, 'latest_info': latest_info})


# API endpoint for retrieving start and end locations for a device
@app.route('/api/start_end_location/<int:device_id>', methods=['GET'])
def get_start_end_location(device_id):
    data = redis_client.hgetall(str(device_id))
    start_location = (float(data[b'start_latitude']), float(data[b'start_longitude']))
    end_location = (float(data[b'end_latitude']), float(data[b'end_longitude']))
    return jsonify({'device_id': device_id, 'start_location': start_location, 'end_location': end_location})


# API endpoint for retrieving all location points for a device within a given time range
@app.route('/api/all_location_points', methods=['GET'])
def get_all_location_points():
    device_id = int(request.args.get('device_id'))
    start_time = pd.to_datetime(request.args.get('start_time'))
    end_time = pd.to_datetime(request.args.get('end_time'))

    data = redis_client.hgetall(str(device_id))
    location_data = data.get(b'location_data')

    if location_data is None:
        return jsonify({'device_id': device_id, 'location_points': []})

    location_data = location_data.decode('utf-8')
    location_data = json.loads(location_data)

    filtered_data = [location for location in location_data if start_time <= pd.to_datetime(location['time_stamp']) <= end_time]

    return jsonify({'device_id': device_id, 'location_points': filtered_data})


# API endpoint to retrieve all data stored in Redis cache
@app.route('/api/all_data', methods=['GET'])
def get_all_data():
    all_data = {}
    for key in redis_client.keys():
        data = redis_client.hgetall(key)
        # Convert byte strings to regular strings
        data = {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}
        data.pop('location_data', None)
        all_data[key.decode('utf-8')] = data
    return jsonify(all_data)




if __name__ == '__main__':

    csv_file = os.getcwd() + '/Raw Data - Backend Developer. (1).csv'
    store_latest_data_in_redis(csv_file)
    app.run(host='0.0.0.0', port=8000)
