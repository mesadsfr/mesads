// https://github.com/webdiscus/html-bundler-webpack-plugin

const path = require("path");
const HtmlBundlerPlugin = require("html-bundler-webpack-plugin");

module.exports = (env, argv) => {
  const isDev = argv.mode === "development";

  const config = {
    mode: isDev ? "development" : "production",
    devtool: isDev ? "inline-source-map" : "source-map",
    stats: "minimal",

    output: {
      path: path.join(__dirname, "./dist_webpack"),
      publicPath: "/static/",
    },

    resolve: {
      alias: {},
      extensions: [".js", ".jsx", ".ts", ".tsx"],
    },

    watchOptions: {
      // Ignore changes in these folders when running `npm run dev`
      ignored: [path.join(__dirname, "mesads/templates/django")],
    },

    plugins: [
      new HtmlBundlerPlugin({
        verbose: false, // output information about the process to console in development mode only
        entry: path.join(__dirname, "mesads/templates/webpack"),

        js: {
          // output filename of extracted JS from source script loaded in HTML via `<script>` tag
          filename: "assets/js/[name].[contenthash:8].js",
        },

        css: {
          // output filename of extracted CSS from source style loaded in HTML via `<link>` tag
          filename: "assets/css/[name].[contenthash:8].css",
        },
      }),
    ],

    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: "ts-loader",
          exclude: /node_modules/,
        },
        // styles
        {
          test: /\.(css|sass|scss)$/,
          use: ["css-loader", "sass-loader", "postcss-loader"],
        },
        // images (load from `images` directory only)
        {
          test: /[\\/]images[\\/].+(png|jpe?g|svg|webp|ico)$/,
          oneOf: [
            // inline image using `?inline` query
            {
              resourceQuery: /inline/,
              type: "asset/inline",
            },
            // auto inline by image size
            {
              type: "asset",
              parser: {
                dataUrlCondition: {
                  maxSize: 1024,
                },
              },
              generator: {
                filename: "assets/img/[name].[hash:8][ext]",
              },
            },
          ],
        },
      ],
    },

    performance: {
      hints: false, // don't show the size limit warning when a bundle is bigger than 250 KB
    },
  };
  return config;
};
