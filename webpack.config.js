const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
  mode: 'development',
  entry: './src/index.js', // Your entry JavaScript file
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'static'),
  },
  devtool: 'inline-source-map',
  devServer: {
    contentBase: './static',
    hot: true, // Enable HMR
  },
  module: {
    rules: [
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.scss$/,
        use: ['style-loader', 'css-loader', 'sass-loader'],
      },
    ],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './src/index.html',
    }),
  ],
};
