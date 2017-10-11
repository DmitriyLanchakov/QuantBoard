from os.path import join

from numpy import where, round
from pandas import DataFrame, read_csv, to_datetime
from flask import Flask, jsonify, make_response, request, abort

import settings
from _private.indicators import Indicators


app = Flask(__name__)


def get_filename(symbol, tf):
    return join(settings.DATA_FOLDER, 
            "DATA_MODEL_{0}_{1}_{2}.csv".format(settings.BROKER, symbol, tf))


def get_dataframe(symbol):
    datas = {}
    for i in settings.TFS:
        data = read_csv(filepath_or_buffer=get_filename(symbol=symbol, tf=i), sep=',', 
            header=0, names=None, index_col=0)
        data.sort_index(axis=0, ascending=True, inplace=True)
        data.index = to_datetime(data.index).to_pydatetime()
        if i == settings.TIMEFRAME:
            data = data.last('12M')
        data.index = data.index.map(str)
        datas[i] = data

    return datas


def get_returns(data):
    datas = {}
    for i in settings.TFS:
        datas[i] = data[i].CLOSE.pct_change().dropna()

    return datas


def get_prob(returns):
    datas = {}
    for i in settings.TFS:
        datas[i] = round(sum(where(returns[i] > 0, 1, 0)) / len(returns[i].index), 2)

    return datas


def get_mean(returns):
    datas = {}
    for i in settings.TFS:
        datas[i] = round(returns[i].mean(), 2)

    return datas


def get_skew(returns):
    datas = {}
    for i in settings.TFS:
        datas[i] = round(returns[i].skew(), 2)

    return datas


def get_data(symbol, indicator, period):
    if settings.USE_LOCAL:
        data = get_dataframe(symbol=symbol)
        indie = Indicators(data=data[settings.TIMEFRAME], period=period, indicator=indicator)
        data[settings.TIMEFRAME] = indie.value()
        returns = get_returns(data=data)
        prob = get_prob(returns=returns)
        returns_mean = get_mean(returns=returns)
        skew = get_skew(returns=returns)

        # 3. get vix status

        j = {
            'symbol': symbol,
            'daily': {
                'skewness': skew[1440],
                'probability': prob[1440],
                'avg_return': returns_mean[1440],
                'data': data[1440].to_dict(orient='index')
            },
            'weekly': {
                'skewness':skew[10080],
                'probability': prob[10080],
                'avg_return': returns_mean[10080]
            },
            'monthly': {
                'skewness': skew[43200],
                'probability': prob[43200],
                'avg_return': returns_mean[43200]
            }
        }
        return j
    else:
        print(">> Non-local data not implemented.")


@app.route('/api/v1.0/symbols', methods=['GET'])
def get_symbols():
    symbols = []
    for s in settings.WATCHLIST_MAP:
        symbol = s.split(",")[0]
        symbols.append({"SYMBOL": symbol})
    return jsonify(symbols)


@app.route('/api/v1.0/data/<string:symbol>/<string:indicator>/<int:period>', methods=['GET'])
def api_data(symbol, indicator, period):
    return jsonify(get_data(symbol=symbol, indicator=indicator, period=period))


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'Error': 'Not found'}), 404)


if __name__ == '__main__':
    app.run(debug=settings.DEBUG)