const path = require('path');

module.exports = {
    entry: path.resolve(__dirname, 'static/js/App.jsx'),
    output: {
        path: path.resolve(__dirname, 'public'),
        filename: 'bundle.js',
        publicPath: '/'
    },
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ['@babel/preset-env', '@babel/preset-react']
                    }
                }
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            }
        ]
    },
    resolve: {
        extensions: ['.js', '.jsx']
    },
    devServer: {
        static: {
            directory: path.join(__dirname, 'public'),
        },
        proxy: {
            '/api': {
                target: '/.netlify/functions',
                pathRewrite: { '^/api': '' }
            }
        },
        port: 3000,
        hot: true,
        historyApiFallback: true
    }
};
