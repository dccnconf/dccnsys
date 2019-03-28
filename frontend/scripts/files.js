(function ($) {
  //////////////////////////////
  // FileInput plugin:
  // consists of a (hidden) <input type="file" ...> and a label with class .dccn-file-name
  // which receives the file name from the <input>.
  //
  // To enable this plugin automatically, wrap the <input> and .dccn-file-name elements
  // inside an element with class '.dccn-file'
  //
  // To use it:
  // * mark the text element to be sed as file name label a class '.dccn-file-name'
  //
  // Example:
  //
  // <div class="dccn-file">
  //   <input type="file" value="Choose file..." name="document">
  //   <p class="dccn-file-name"></p>
  // </div>
  //
  $.fn.dccnFileInput = function () {
    var label = this.find('.dccn-file-name');
    var input = this.find('input[type="file"]');
    input.on('change', function () {
      if (this.files && this.files[0]) {
        label.text(this.files[0].name);
      }
    });
    return this;
  };

  /////////////////////////////////////
  // Submit load indication
  //
  // Using this plugin allows to show a spinner indicator instead of 'Save' button while waiting
  // for the server response on submit.
  //
  // Example:
  //
  // <button type="submit" class="dccn-submit btn btn-success" data-form="#theForm">
  //   <span class="dccn-submit-indicator spinner-border spinner-border-sm d-none"></span>
  //   Submit...
  // </button>
  //
  $.fn.dccnFormSubmitIndicator = function () {
    var form = $(this.attr('data-form'));
    form.submit(event => {
      var indicator = this.find('.dccn-submit-indicator');
      this.prop('disabled', true);
      indicator.removeClass('d-none');
    });
    return this;
  };

  //////////////////////////////////////////
  // File view and delete plugin (file-vd)
  //
  // Expected to have a link to view the file and a form to delete it. To make things work,
  // HTML must contain a `.dccn-file-vd` element, inside which there will be a form and an
  // area to view the file and have a delete link (see the example). The form must have
  // `.dccn-file-vd-form` class, the area - `.dccn-file-vd-box` class.
  //
  // When the delete form is submitted, the plugin initiates an AJAX submit using
  // XMLHttpRequest API. Upon receiving the response, it replaces the working area
  // (which is marked with `.dccn-file-vd-form` class) with the response content.
  // It is expected that the response contains HTML.
  //
  // Example:
  //
  // <div class="dccn-file-vd">
  //   <form class="dccn-file-vd-form" action="/item/delete" method="POST" id="form1"></form>
  //   <div class="dccn-file-vd-box">
  //     <p><a href="/item/view">press to view the file</a></p>
  //     <button type="submit" form="form1">Delete</button>
  //   </div>
  // </div>
  $.fn.dccnFileVD = function () {
    var form = this.find('.dccn-file-vd-form');
    var box = this.find('.dccn-file-vd-box');
    form.on('submit', event => {
      var req = new XMLHttpRequest();
      req.onload = () => { box.html(req.response); };
      req.open(form.attr('method'), form.attr('action'), true);
      req.send(new FormData(form.get(0)));
      event.preventDefault();
      return false;
    });
    return this;
  };


  //////////////////////////////
  // Associating the plugins
  $('.dccn-file').dccnFileInput();
  $('.dccn-submit').dccnFormSubmitIndicator();
  $('.dccn-file-vd').dccnFileVD();
}(jQuery));
