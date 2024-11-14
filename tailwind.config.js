/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./static/**/*.{js, css}","./static/**/**/*.{css , js}" ,"./templates/*.html", "./templates/**/*.html", "./templates/**/**/*.html", "./templates/**/**/**/*.html", "./templates/**/**/**/**/*.html"],
  theme: {
    screens: {
      'xs': '225px',
      'xsm': '324px',
      'after-xsm': '400px',
      'xxsm': '478px',
      'sm': '640px',
      // => @media (min-width: 640px) { ... }

      'md': '768px',
      // => @media (min-width: 768px) { ... }

      'pre-lg': '878px',
      // => @media (min-width: 878px) { ... }

      'lg': '1024px',
      // => @media (min-width: 1024px) { ... }

      'xl': '1280px',
      // => @media (min-width: 1280px) { ... }

      '2xl': '1536px',
      // => @media (min-width: 1536px) { ... }
      '3xl': '2000px'
    },
    fontSize: {
      'Tiny': '10px',
      'XSmall': '12px',
      'Small': '14px',
      'Base': '16px',
      'Semi-Medium': '17px',
      'Medium': '18px',
      'Large': '20px',
      'Pre-Xl': '22px',
      'xl': '24px',
      '1xl': '27px',
      '2xl': '30px',
      '3xl': '36px',
      '3.5xl': '42px',
      '4xl': '48px',
      '5xl': '60px',
      '6xl': '72px',
      '7xl': '84px',
      '8xl': '96px',
      '9xl': '120px',
      '10xl': '144px',
      '11xl': '168px',
      '12xl': '192px',
      '13xl': '216px',
      '14xl': '240px',
      '15xl': '264px',
      '16xl': '288px',
      '17xl': '312px',
      '18xl': '336px',
      '19xl': '360px',
      '20xl': '384px',
      '21xl': '408px',
      '22xl': '432px',
      '23xl': '456px',
      '24xl': '480px',
      '25xl': '504px',
      '26xl': '528px',
      '27xl': '552px',
      '28xl': '576px',
      '29xl': '600px',
    },
    extend: {
      backdropBlur: {
        '105': '105px',
        '120': '120px',
      },
      backdropSaturate: {
        '170': '1.7'
      },
      fontFamily: {
        'Choleric': ['Choleric', 'sans-serif'],
        'Wanted-ExtraBlack': ['Wanted-ExtraBlack', 'sans-serif'],
        'Wanted-Black': ['Wanted-Black', 'sans-serif'],
        'Wanted-ExtraBold': ['Wanted-ExtraBold', 'sans-serif'],
        'Wanted-SemiBold': ['Wanted-SemiBold', 'sans-serif'],
        'Wanted-Bold': ['Wanted-Bold', 'sans-serif'],
        'Wanted-Medium': ['Wanted-Medium', 'sans-serif'], 
        'Wanted-Regular': ['Wanted-Regular', 'sans-serif'],
        'Wanted-Variable' : ['Wanted-Variable', 'sans-serif']
      },
      borderColor: {
        'custom-rgba': 'rgba(9, 9, 9, 0.108)',
        'custom-rgba2': 'rgba(62, 62, 62, 0.257)',
        'custom-rgba3': 'rgba(13, 13, 13, 0)',
        'custom-rgba4': 'rgba(0, 0, 0, 0.19)',
        'custom-rgba5': 'rgba(113, 113, 113, 0.182)',
        'custom-rgba6': 'rgba(116, 116, 116, 0.031)',
        'custom-rgba7': 'rgba(33, 33, 33, 0.657)',
        'custom-rgba8': 'rgba(0, 0, 0, 0.038)',
      },
      boxShadow: {
        'custom-shadow': '2px 3px 21px 4px rgba(62, 62, 62, 0.257);',
        'custom': '3px 6px 9px -3px rgba(17, 17, 26, 0.305)',
        'custom-shadow-2': '2px 3px 21px 4px rgba(0, 0, 0, 0.061)',
        'custom-shadow-3': '2px 3px 21px 4px rgba(170, 170, 170, 0.075)',
        'form-shadow': '2px 3px 21px 4px rgba(138, 138, 138, 0.026)',
        'form-shadow-2': '2px 3px 21px 4px rgba(0, 0, 0, 0.061)',
        'custom-shadow-4': '0px 4px 12px rgba(0, 0, 0, 0.272)',
        'custom-shadow-5': '2px 3px 21px 4px rgba(0, 0, 0, 0.289)',
      },
      colors: {
        customGray: 'rgb(120, 120, 120)',
        customGray2: 'rgb(99, 99, 99)',
        customGray3: 'rgba(128, 128, 128, 0.798)',
        customGray4: 'rgba(146, 146, 146, 0.096)',
        customGray5: 'rgba(66, 66, 66, 0.575)',
        'gradient-start': '#008d95bc',
        'gradient-end': '#13c9d3',
        'green': '#008d95',
        'customColor': 'rgba(66, 66, 66, 0.575)',
      },
      zIndex: {
        '1': '1',
        '2': '2',
        '3': '3',
        '4': '4',
        '5': '5',
        '6': '6',
        '10': '10',
        '1000': '1000',
        '1010' : '1010',
      },
      top: {
        '30': '30%',
      },
      spacing: {
        '30': '30rem',
        '66': '18rem',
      },
      borderRadius: {
        '3.0': '3.0rem',
        '3.8': '3.8rem',
      },
      backgroundColor: ['active'],
      width: ['responsive'],
    },
  },
  plugins: [],
}

