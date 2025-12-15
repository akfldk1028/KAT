const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const TsconfigPathsPlugin = require('tsconfig-paths-webpack-plugin');
module.exports = {
  mode: 'development',

  entry: "./src/index.tsx",

  resolve: {
    extensions: [".ts", ".tsx", '.js'],
    plugins: [new TsconfigPathsPlugin({ configFile: "./tsconfig.json" })]
  },
  devtool: "source-map",
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loader: "babel-loader",
        exclude: /node_modules/
      }
    ]
  },
  devServer: {
    static: {
      directory: path.resolve(__dirname, "public"),
    },
    compress: true,
    historyApiFallback: true,
    port: 3000,
    open: true,
  },
  output: {
    path: path.resolve(__dirname, "build"),
    publicPath: "/",
    filename: "[chunkhash]_bundle.js"
  },
 
  plugins: [
    new HtmlWebpackPlugin({
      template: path.resolve(__dirname, "./public/index.html"),
    }),
    new CleanWebpackPlugin({
      cleanAfterEveryBuildPatterns: ['build']
    })
  ]
};