function Feed(columnId) {
    this.selector = {
        results: '#feed-' + columnId,
        loader: '#loader-' + columnId,
        settings: '#settings-' + columnId
    };
    this.init();
};


Feed.prototype.fetch = function() {
    var _this = this;
    var serializedData = $(this.selector.settings).serializeArray();
    var postData = {};
    serializedData.forEach(function (elem) {
        postData[elem['name']] = elem['value'];
    });
    $.ajax({
        beforeSend: function (xhr) {
            $(_this.selector.loader).toggle();
            $(_this.selector.results).html('');
            xhr.setRequestHeader('Content-Type', 'application/json');
        },
        data: JSON.stringify(postData),
        method: 'POST',
        url: '/feed/generate'
    }).always(function () {
        $(_this.selector.loader).toggle();
    }).done(function (data) {
        $(_this.selector.settings).parent('.settings').prop('open', null);
        $(_this.selector.results).html(data);
    }).fail(function (data) {
        window.console.log(data);
    });
}

Feed.prototype.init = function() {
    var _this = this;
    $(this.selector.settings).submit(function( event ) {
      event.preventDefault();
      _this.fetch();
    });
};

$(document).ready(function() {
    // Auto-fetch the first two feeds (we have default settings).
    var feed1 = new Feed('1');
    feed1.fetch();
    var feed2 = new Feed('2');
    feed2.fetch();
    // Don't fetch the last feed, it's for user-generated settings.
    var feed3 = new Feed('3');
});
