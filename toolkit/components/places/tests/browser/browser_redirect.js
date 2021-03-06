/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

function test() {
  waitForExplicitFinish();

  const REDIRECT_URI = NetUtil.newURI("http://mochi.test:8888/tests/toolkit/components/places/tests/browser/redirect.sjs");
  const TARGET_URI = NetUtil.newURI("http://mochi.test:8888/tests/toolkit/components/places/tests/browser/redirect-target.html");

  gBrowser.selectedTab = gBrowser.addTab();
  registerCleanupFunction(function() {
    gBrowser.removeCurrentTab();
  });
  gBrowser.selectedTab.linkedBrowser.loadURI(REDIRECT_URI.spec);

  // Create and add history observer.
  let historyObserver = {
    onVisit: function (aURI, aVisitID, aTime, aSessionID, aReferringID,
                      aTransitionType) {
      info("Received onVisit: " + aURI.spec);
      PlacesUtils.history.removeObserver(historyObserver);

      ok(aURI.equals(TARGET_URI), "The redirect source should not be notified");

      fieldForUrl(REDIRECT_URI, "frecency", function (aFrecency) {
        ok(aFrecency != 0, "Frecency or the redirecting page should not be 0");

        fieldForUrl(REDIRECT_URI, "hidden", function (aHidden) {
          is(aHidden, 1, "The redirecting page should be hidden");

          fieldForUrl(TARGET_URI, "frecency", function (aFrecency) {
            ok(aFrecency != 0, "Frecency of the target page should not be 0");

            fieldForUrl(TARGET_URI, "hidden", function (aHidden) {
              is(aHidden, 0, "The target page should not be hidden");

              promiseClearHistory().then(finish);
            });
          });
        });
      });
    },
    onBeginUpdateBatch: function () {},
    onEndUpdateBatch: function () {},
    onTitleChanged: function () {},
    onBeforeDeleteURI: function () {},
    onDeleteURI: function () {},
    onClearHistory: function () {},
    onPageChanged: function () {},
    onDeleteVisits: function () {},
    QueryInterface: XPCOMUtils.generateQI([Ci.nsINavHistoryObserver])
  };
  PlacesUtils.history.addObserver(historyObserver, false);
}
