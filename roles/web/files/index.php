<?php
declare(strict_types=1);

$config = require '/etc/ad10-app.php';
$server = gethostname();
$database = null;
$products = [];
$error = null;

try {
    $connection = new PDO(
        sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $config['host'], $config['port'], $config['database']),
        $config['user'],
        $config['password'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_TIMEOUT => 3]
    );
    $database = $connection->query('SELECT @@hostname')->fetchColumn();
    $products = $connection->query('SELECT name, price FROM products ORDER BY id')->fetchAll(PDO::FETCH_ASSOC);
} catch (PDOException $exception) {
    http_response_code(503);
    $error = 'La base de données est temporairement indisponible.';
    error_log('Database connection failed.');
}

function escape(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
?>
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cluster web AD10</title>
    <style>
        body { font: 18px/1.6 system-ui, sans-serif; margin: 64px auto; max-width: 850px; padding: 0 24px; color: #172033; background: #f5f7fb; }
        main { background: white; padding: 40px; border: 1px solid #dce2eb; border-radius: 12px; }
        h1 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #dce2eb; }
        .status { color: #17613c; }
        .error { color: #a42121; }
    </style>
</head>
<body><main>
    <h1>Cluster web AD10</h1>
    <p>Serveur web : <strong><?= escape((string) $server) ?></strong></p>
    <?php if ($error !== null): ?>
        <p class="error"><?= escape($error) ?></p>
    <?php else: ?>
        <p class="status">Service disponible. Base de données : <strong><?= escape((string) $database) ?></strong>.</p>
        <h2>Catalogue de test</h2>
        <table><thead><tr><th>Produit</th><th>Prix</th></tr></thead><tbody>
        <?php foreach ($products as $product): ?>
            <tr><td><?= escape($product['name']) ?></td><td><?= escape($product['price']) ?> €</td></tr>
        <?php endforeach; ?>
        </tbody></table>
    <?php endif; ?>
</main></body></html>
