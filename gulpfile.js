/* jshint esversion: 6 */
const gulp = require('gulp');
const browserSync = require('browser-sync');
const sass = require('gulp-sass');
const del = require('del');
const concat = require('gulp-concat');
const concatCss = require('gulp-concat-css');
const uglify = require('gulp-uglify-es').default;
const argv = require('yargs').argv;

const DESTINATION = 'wwwdccn/static';
const SOURCE = 'frontend';
const CSS_BUNDLE_NAME = 'dccn-ui.css';
const JS_BUNDLE_NAME = 'dccn-ui.js';

const paths = {
    styles: {
        source: `${SOURCE}/scss/**/*.scss`,
        destination: `${DESTINATION}/css`
    },
    scripts: {
        source: `${SOURCE}/**/*.js`,
        destination: `${DESTINATION}/scripts`
    },
    html: {
        source: `${SOURCE}/**/*.html`
        // destination: `${DESTINATION}/`
    },
    images: {
        source: `${SOURCE}/images/*`,
        destination: `${DESTINATION}/images`
    },
    externalScripts: [
        'node_modules/jquery/dist/jquery.min.js',
        'node_modules/popper.js/dist/popper.min.js',
        'node_modules/bootstrap/dist/js/bootstrap.bundle.js',
        'node_modules/sweetalert2/dist/sweetalert2.min.js',
        'node_modules/mathjs/dist/math.js',
        'node_modules/chart.js/dist/Chart.bundle.min.js',
        'node_modules/requirejs/require.js',
        'node_modules/bootbox/dist/bootbox.min.js',
    ],
    externalStyles: [
        'node_modules/sweetalert2/dist/sweetalert2.min.css',
    ],
    codeMirror: 'node_modules/codemirror',
};

function fonts() {
  return gulp.src('node_modules/@fortawesome/fontawesome-free/webfonts/*')
    .pipe(gulp.dest(`${DESTINATION}/webfonts`));
}

function styles() {
    return gulp.src(paths.styles.source)
        .pipe(sass()).on("error", sass.logError)
        .pipe(concatCss(CSS_BUNDLE_NAME))
        .pipe(gulp.dest(paths.styles.destination))
        .pipe(browserSync.stream());
}

function scripts() {
    return gulp.src(paths.scripts.source)
        .pipe(concat(JS_BUNDLE_NAME))
        .pipe(uglify())
        .pipe(gulp.dest(paths.scripts.destination))
        .pipe(browserSync.stream());
}

function copyExternalScripts() {
  return gulp.src(paths.externalScripts)
    .pipe(gulp.dest(paths.scripts.destination));
}

function copyNodeModules() {
    return gulp.src([
      `node_modules/codemirror/**`,
    ], {
        base: 'node_modules/'
    }).pipe(gulp.dest(DESTINATION));
}

function copyAssets() {
    return gulp.src([
      `${SOURCE}/assets/**`,
    ], {
        base: SOURCE
    }).pipe(gulp.dest(DESTINATION))
}

function copyExternalStyles() {
    return gulp.src(paths.externalStyles)
        .pipe(gulp.dest(paths.styles.destination));
}

function html(cb) {
    if (!argv.production) {
        return gulp.src(paths.html.source)
            // .pipe(gulp.dest(paths.html.destination))
            .pipe(browserSync.stream());
    }
    cb();
}

function images() {
    return gulp.src(paths.images.source)
      .pipe(gulp.dest(paths.images.destination))
      .pipe(browserSync.stream());
}

function clean(cb) {
    del([`${paths.styles.destination}`]);
    del([`${paths.scripts.destination}`]);
    del([`${paths.images.destination}`]);
    del([`${DESTINATION}/webfonts`]);
    // Remove modules:
    del([`${DESTINATION}/codemirror`]);
    cb();
}

function serve() {
    browserSync.init({server: [`${DESTINATION}`, `${SOURCE}/samples`]});
    gulp.watch(paths.styles.source, styles);
    gulp.watch(paths.scripts.source, scripts);
    gulp.watch(paths.html.source, html);
    gulp.watch(paths.images.source, images);
}

const copyExternals = gulp.parallel(copyExternalScripts, copyExternalStyles, copyNodeModules, copyAssets);

const build = gulp.parallel(styles, scripts, images, fonts, copyExternals);

exports.build = build;
exports.clean = clean;
exports.serve = serve;
exports.default = gulp.series(clean, build, serve);
