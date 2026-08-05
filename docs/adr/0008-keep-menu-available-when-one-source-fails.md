# Keep Menu Available When One Source Fails

PicMenu Next treats help data collection as best-effort: one broken plugin metadata record, external menu config file, or Mixin should not make the whole help menu unavailable. Failed sources are skipped after warning, and the remaining collected menu data continues through rendering. Mixin changes are not transactional, so PicMenu Next does not roll back in-place mutations made before a Mixin fails.
