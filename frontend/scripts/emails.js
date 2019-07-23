(function ($) {
  $.fn.dccnSentEmailInstanceView = function () {
    console.log('123');
    console.log(this);
  };


  //////////////////////////////
  // Associating the plugins
  $('.dccn-sent-email-instance-view').dccnSentEmailInstanceView();
}(jQuery));
