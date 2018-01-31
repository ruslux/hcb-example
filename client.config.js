var path = require('path');
var fs = require('fs');
var ExtractTextWebpackPlugin = require('extract-text-webpack-plugin');


var nodeModules = {};
fs.readdirSync('node_modules')
    .filter(function (x) {
        return ['.bin'].indexOf(x) === -1;
    })
    .forEach(function (mod) {
        nodeModules[mod] = 'commonjs ' + mod;
    });

module.exports = {
    entry: './src/client/app.js',
    target: 'web',
    output: {
        filename: 'app.js',
        path: path.resolve(__dirname, 'static/build/')
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules\/(?!src)/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        babelrc: false,
                        presets: ['babel-preset-env'],
                        plugins: ['babel-plugin-transform-runtime', 'angularjs-annotate']
                    }
                }
            },
            {
                test: /\.styl$/,
                exclude: /node_modules\/(?!src)/,
                use: ExtractTextWebpackPlugin.extract(
                    {
                        use: [
                            'css-loader',
                            'stylus-loader'
                        ]
                    }
                )
            }
        ]
    },
    plugins: [
        new ExtractTextWebpackPlugin("app.css")
    ]
};
