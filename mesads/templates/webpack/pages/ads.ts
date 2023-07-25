import Alpine from "alpinejs";

// array.findLastIndex is only available for firefox>104
function findLastIndex(arr: any[], func: (e: any) => boolean) {
  for (let i = arr.length; i > 0; --i) {
    if (func(arr[i - 1])) {
      return i - 1;
    }
  }
  return -1;
}

type DataType = {
  ads_creation_date: string;
  used_by_owner: string;
  attribution_type: string;
};

const data = JSON.parse(
  (document.getElementById("data") as HTMLScriptElement).text
) as DataType;

Alpine.data("get_x_data", () => ({
  ads_creation_date: data.ads_creation_date,

  get ads_before_2014() {
    const creation_date = new Date(this.ads_creation_date);
    if (creation_date >= new Date("2014-10-01")) {
      return false;
    }
    return true;
  },

  // The field "attribution_date" should only be displayed for old ADS, or if the creation date is not set
  get should_display_attribution_date() {
    return !this.ads_creation_date || this.ads_before_2014;
  },

  used_by_owner: data.used_by_owner,

  // The field "owner_license_number" should always be displayed for new ADS.
  // For old ADS, it should only be displayed if the field "used_by_owner" is
  // set to "true"
  get should_display_owner_license_number() {
    return (
      !this.ads_before_2014 ||
      this.used_by_owner === "true" ||
      this.used_by_owner === "unknown"
    );
  },

  attribution_type: data.attribution_type,
  numberOfADSUsersFormsetToDisplay: (() => {
    // All forms
    const ads_user_forms = Array.from(
      document.getElementsByClassName("ads-user-form")
    );
    // List, returns true if the form is empty, false otherwise
    const filled = ads_user_forms.map(
      (e) => !!e.querySelector('input:not([type="hidden"]):not([value=""])')
    );
    // Index of the first non-empty form
    const nonEmptyFormIdx = findLastIndex(filled, (e) => e === true);
    // All the forms are empty, display only one blank form
    if (nonEmptyFormIdx < 0) {
      return 1;
    }
    return nonEmptyFormIdx + 1;
  })(),
}));

Alpine.start();
