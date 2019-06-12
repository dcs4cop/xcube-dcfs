//VERSION=3
function setup() {
    return {
      input: [{
        bands: ["B02", "B03", "B04", "B08"],
        units: "reflectance",
      }],
      output: [
        {
          id: "rgb",
          bands: 3,
        }, {
          id: "falseColor",
          bands: 3,
        }
      ]
    };
}

function evaluatePixel(sample) {
  return {
    rgb: [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02],
    falseColor: [2.5 * sample.B08, 2.5 * sample.B04, 2.5 * sample.B03],
  };
}
