const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const ForkTsCheckerWebpackPlugin = require('fork-ts-checker-webpack-plugin');

module.exports = (_env, argv) => {
  const isProd = process.env.NODE_ENV === 'production' || argv.mode === 'production';
  return {
    entry: './src/index.tsx',
    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: 'assets/[name].[contenthash].js',
      publicPath: '/',
      clean: true,
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: {
            loader: 'ts-loader',
            options: { transpileOnly: true },
          },
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: [
            isProd ? MiniCssExtractPlugin.loader : 'style-loader',
            'css-loader',
            'postcss-loader',
          ],
        },
      ],
    },
    resolve: { extensions: ['.tsx', '.ts', '.js'] },
    plugins: [
      new HtmlWebpackPlugin({ template: 'src/index.html' }),
      new CopyWebpackPlugin({ patterns: [{ from: 'public', to: '.' }] }),
      new ForkTsCheckerWebpackPlugin(),
      ...(isProd
        ? [new MiniCssExtractPlugin({ filename: 'assets/[name].[contenthash].css' })]
        : []),
    ],
    devServer: {
      port: 3001,
      historyApiFallback: true,
      proxy: [{ context: ['/api'], target: 'http://localhost:8002' }],
    },
    devtool: isProd ? 'source-map' : 'eval-cheap-module-source-map',
  };
};
