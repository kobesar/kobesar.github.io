var ghpages = require('gh-pages');

ghpages.publish(
    'public', // path to public directory
    {
        branch: 'refresh',
        repo: 'https://github.com/kobesar/kobesar.github.io.git', // Update to point to your repository  
        user: {
            name: 'Kobe Sarausad', // update to use your name
            email: 'klobby19@gmail.com' // Update to use your email
        }
    },
    () => {
        console.log('Deploy Complete!')
    }
)