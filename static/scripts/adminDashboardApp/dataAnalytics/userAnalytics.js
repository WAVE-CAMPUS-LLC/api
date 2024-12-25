const express = require('express');
const { Client } = require('pg');
const app = express();
const client = new Client({
    connectionString: process.env.DATABASE_URL,
});

client.connect();

app.get('/api/userAnalytics', async (req, res) => {
    const result = await client.query('SELECT COUNT(*) FROM customuser');
    res.json({ userCount: result.rows[0].count });
});

app.listen(process.env.PORT || 3000, () => {
    console.log('Server started');
});