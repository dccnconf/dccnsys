//
// Original code was taken from https://github.com/Foliotek/Croppie/blob/master/demo/demo.js
//
(function ($) {
  $.fn.dccnAvatar = function(action, options) {
    var $wrap = this.find('.dccn-upload-wrap');
    var $msg = this.find('.dccn-upload-msg');
    var $frame = $wrap.find('.dccn-upload-frame');
    var $input = this.find('.dccn-file-input input');
    var $controls = this.find('.dccn-upload-control');

    // Define a default action - popup an image in a separate window.
    // In real world, here we will send an AJAX POST.
    var popupImage = function (src) {
      swal({
        title: '',
        content: { element: 'img', attributes: { 'src': src } },
        allowOutsideClick: true
      });
    };

    // This function loads data from the file input into the croppie frame.
    var readFile = function (input) {
      if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
          if (!$wrap.hasClass('ready')) {
            $wrap.addClass('ready');
          }
          if (!$msg.hasClass('hidden')) {
            $msg.addClass('hidden');
          }
          $frame.croppie('bind', {
            url: e.target.result
          }).then(function() {
            console.log('jQuery bind complete');
          });
        };
        reader.readAsDataURL(input.files[0]);
      } else {
        console.log("Sorry - you're browser doesn't support the FileReader API");
      }
    };

    var attach = function ($el, settings) {
      var $result = $controls.filter('.dccn-upload-control-result');
      var $rotateLeftCtrl = $controls.filter('.dccn-upload-control-rotate-left');
      var $rotateRightCtrl = $controls.filter('.dccn-upload-control-rotate-right');

      $frame.croppie({
        viewport: {
          width: settings.intSize,
          height: settings.intSize,
          type: 'circle'
        },
        boundary: {
          width: settings.extSize,
          height: settings.extSize
        },
        enableOrientation: true
      });

      $input.on('change', function() {
        readFile(this);
      });

      $result.on('click', function(ev) {
        $frame.croppie('result', {
          type: 'canvas',
          size: 'viewport'
        }).then(settings.fn);
      });

      $rotateLeftCtrl.on('click', function () {
        $frame.croppie('rotate', 90);
      });
      $rotateRightCtrl.on('click', function () {
        $frame.croppie('rotate', -90);
      });
    };

    var detach = function () {
      $wrap.removeClass('ready');
      $msg.removeClass('hidden');
      $frame.croppie('destroy');
      $controls.off('click');
      $input.val("");  // !! otherwise no reaction whenever loading same avatar
    };

    //
    // --- main function ---
    //
    var settings = $.extend({
      extSize: 300,
      intSize: 250,
      fn: popupImage
    }, options);

    if (!action || (action === 'attach')) {
      attach(this, settings);
    }
    else if (action === 'detach') {
      detach();
    }

    return this;
  };
}(jQuery));
